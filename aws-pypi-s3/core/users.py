import json
import boto3
import hashlib
import botocore.exceptions

from datetime import datetime
from typing import Dict, List

from core.utils import random_string


class UserStore:

    def __init__(self, bucket_name: str) -> None:
        self.__client = boto3.resource('s3')
        self.__bucket_name = bucket_name

    def set(self, username: str, password: str) -> None:
        user_store = self.__load_users_store()
        data = user_store.get(username, {})
        data['salt'] = random_string(10)
        data['password'] = hashlib.md5(bytes(f"{password}{data['salt']}", 'utf-8')).hexdigest()
        data['updated_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

        if not data.get('created_at', None):
            data['created_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')

        user_store.update({username: data})
        self.__upload_users_store(user_store)

    def get(self, username: str) -> Dict:
        user_store = self.__load_users_store()

        data = {}
        data['username'] = username
        data.update(user_store.get(username, {}))
        return data

    def delete(self, username: str):
        user_store = self.__load_users_store()
        user_store.pop(username)
        self.__upload_users_store(user_store)

    def verify_password(self, username: str, password: str) -> bool:
        user = self.get(username)
        password = hashlib.md5(bytes(f"{password}{user['salt']}", 'utf-8')).hexdigest()
        return user.get('password') == password

    def list(self) -> List[Dict]:
        user_store = self.__load_users_store()

        users = []
        for user in user_store:
            data = user_store.get(user, {})
            users.append(f"username: {user} -> created_at: {data['created_at']}")
        return '\n'.join(users)

    def __load_users_store(self) -> Dict:
        try:
            users_store = self.__client.Object(self.__bucket_name, 'configs/users')
            return json.loads(users_store.get()['Body'].read())
        except botocore.exceptions.ClientError:
            return {}

    def __upload_users_store(self, data: Dict = dict()) -> None:
        users_store = self.__client.Object(self.__bucket_name, 'configs/users')
        users_store.put(Body=json.dumps(data))
