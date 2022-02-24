import boto3
import logging

from core.users import UserStore
from core.storage import Storage
from core.utils import auth_decode

from typing import Dict, NewType, Tuple, Union


log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.INFO)


Request = NewType('Request', Dict)
Response = NewType('Response', Dict)

UNAUTHORIZED_RESPONSE = Response(
    {
        "status": "401",
        "statusDescription": "Unauthorized",
        "headers": {
            "www-authenticate": [{"key": "WWW-Authenticate", "value": "Basic"}]
        }
    }
)
NOTFOUND_EVENT_RESPONSE = Response(
    {
        "status": "404",
        "statusDescription": "Not Found"
    }
)
UNSUPPORTED_METHOD_RESPONSE = Response(
    {
        "status": "405",
        "statusDescription": "Method not allowed"
    }
)
UNEXPECTED_EVENT_RESPONSE = Response(
    {
        "status": "405",
        "statusDescription": "Unexpected LambdaEdge event"
    }
)


class UnexpectEventException(Exception):
    pass


class UnsupportedMethodException(Exception):
    pass


class UnauthorizedException(Exception):
    pass


class NotFoundException(Exception):
    pass


def content_filter(request: Request, bucket_name: str) -> Request:
    path = request.get("uri", "")

    storage = Storage(bucket_name)
    if not storage.package_exists(path):
        raise NotFoundException(f'Package not found. {path}')

    if path.endswith("/"):
        request["uri"] = path + "index.html"
    return request


def authorize(request: Request, bucket_name: str):
    try:
        credentials: str = get_header_value(request, 'authorization')
        if not credentials:
            raise UnauthorizedException('Authentication header not found')
        
        username, password = auth_decode(credentials)
        user_store = UserStore(bucket_name)
        
        if not user_store.verify_password(username, password):
            raise UnauthorizedException(f'user not allowed: {username}')
        
        return request
    except Exception as ex:
        log.error(ex)
        if isinstance(ex, UnauthorizedException):
            raise ex
        raise UnauthorizedException("cannot decode basic auth header")


def get_header_value(request: Request, header_name: str):
        authorization_header = {
            k.lower(): v
            for k, v in request.get("headers", {}).items()
            if k.lower() == header_name
        }.get(header_name)
        if authorization_header:
            return authorization_header[0].get("value")
        return None


def get_bucket_name(distribution_id: str):
    cloudfront = boto3.client('cloudfront')
    response = cloudfront.get_distribution_config(Id=distribution_id)
    config = response.get('DistributionConfig', {})
    origens = config.get('Origins', {}).get("Items", [])
    if len(origens) == 0:
        raise Exception('Origens not found')
    bucket_dn = origens[0].get('DomainName', None)
    return bucket_dn.rsplit(".", maxsplit=4)[0]


def extract_data(event: Dict) -> Tuple[Dict, str]:
    cf_config = event.get('config', {})
    cf_request = Request(event.get('request', {}))

    method = cf_request.get('method', None)
    event_type = cf_config.get('eventType', None)
    distribution_id = cf_config.get('distributionId', None)

    if not event_type == 'viewer-request':
        raise UnexpectEventException(f'unexpected event type "{event_type}"')

    if method not in {'GET', 'HEAD'}:
        raise UnsupportedMethodException(f'unsupported method "{method}"')

    return cf_request, distribution_id


def handler(event: Dict, context: Dict) -> Union[Request, Response]:
    try:
        records = event.get('Records', [{'cf': {}}])
        for record in records:
            request, distribution_id = extract_data(record.get('cf', {}))
            bucket_name = get_bucket_name(distribution_id)
            authorize(request, bucket_name)
            return content_filter(request, bucket_name)

    except NotFoundException as ex:
        log.warning("package not found: %s", str(ex))
        return NOTFOUND_EVENT_RESPONSE

    except UnauthorizedException as ex:
        log.warning("access denied: %s", str(ex))
        return UNAUTHORIZED_RESPONSE

    except UnsupportedMethodException as ex:
        log.warning("request method denied: %s", str(ex))
        return UNSUPPORTED_METHOD_RESPONSE

    except UnexpectEventException as ex:
        log.critical("Unexpect Event Error: %s", str(ex))
        return UNEXPECTED_EVENT_RESPONSE

    except Exception as ex:
        log.critical("Internal Error: %s", str(ex))
        return UNEXPECTED_EVENT_RESPONSE