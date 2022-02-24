from sys import prefix
import boto3
import botocore.exceptions

from core.utils import get_path


class Storage:

    def __init__(self, bucket_name: str, index: str = 'index.html') -> None:
        self.__client = boto3.resource('s3')
        self.__bucket_name = bucket_name
        self.__index = index

    def get_index(self):
        data = self.__client.Object(self.__bucket_name, self.__index)
        try:
            return data.get()['Body'].read().decode('utf-8')
        except botocore.exceptions.ClientError:
            return ''

    def upload_package(self, package, dist_path: str = None):
        for filename in package.files:
            path = f'{get_path(dist_path)}/{filename}'
            with open(path, mode='rb') as f:
                self.__client.Object(self.__bucket_name, f'{package.name}/{filename}').put(
                    Body=f,
                    ContentType='application/x-gzip',
                    ACL='private'
                )

    def upload_index(self, html: str):
        self.__client.Object(self.__bucket_name, self.__index).put(
            Body=html,
            ContentType='text/html',
            CacheControl='public, must-revalidate, proxy-revalidate, max-age=0',
            ACL='private'
        )

    def package_exists(self, path: str):
        client = boto3.client('s3')

        prefix = path
        if prefix.startswith('/'):
            prefix = prefix[1:] if len(prefix) > 1 else prefix

        files = client.list_objects(Bucket=self.__bucket_name, Prefix=prefix)
        return len(files.get('Contents', [])) > 0