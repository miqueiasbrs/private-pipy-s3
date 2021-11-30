import json
import boto3

from hashlib import md5
from botocore.exceptions import ClientError

s3_client = boto3.resource('s3')

class S3UserStore:

    __key: str = None
    __bucket_name: str = None
    __refresh_period: float = None
    
    def __init__(
        self,
        bucket_name: str,
        key: str,
        refresh_period: float = 60.0
    ) -> None:
        self.__bucket_name = bucket_name
        self.__key = key

    def __get_user_store(self):
        try:
            data = s3_client.Object(
                bucket_name=self.__bucket_name,
                key=self.__key
            )
            data.load()
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                data.put(Body=json.dumps({}))
                return self.__get_user_store()
            else:
                raise e

    def __get(self, data) -> dict:
        return json.loads(data.get()['Body'].read())

    def add(self, username: str, password: str, *args):
        password = md5(bytes(password, 'utf-8')).hexdigest()
        data = self.__get_user_store()
        users: dict = self.__get(data)
        users.update({ username: password })
        data.put(Body=json.dumps(users))

    def remove(self, username: str, *args):
        data = self.__get_user_store()
        users: dict = self.__get(data)
        users.pop(username, None)
        data.put(Body=json.dumps(users))
