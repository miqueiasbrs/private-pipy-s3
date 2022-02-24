import os
import random
import string
import base64

from typing import Tuple


def random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))


def get_path(relative_path: str) -> str:
    path = os.path.join(os.getcwd(), relative_path)
    return os.path.abspath(path)


def auth_decode(encoded: str) -> Tuple[str, str]:
    split = encoded.strip().split(' ')
    if len(split) == 1:
        try:
            username, password = base64.b64decode(split[0]).decode().split(':', 1)
        except:
            raise Exception('DecodeError')

    elif len(split) == 2:
        if split[0].strip().lower() == 'basic':
            try:
                username, password = base64.b64decode(split[1]).decode().split(':', 1)
            except:
                raise Exception('DecodeError')

    else:
        raise Exception('DecodeError')

    return username, password
