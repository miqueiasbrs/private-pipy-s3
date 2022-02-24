import os
import sys
import getpass

from typing import Sequence
from core.users import UserStore
from argparse import ArgumentParser, Namespace


def set_user(args: Namespace) -> None:
    user_store = UserStore(args.bucket_name)
    user_store.set(args.username, getpass.getpass())


def list_users(args: Namespace) -> None:
    user_store = UserStore(args.bucket_name)
    print(user_store.list())


def del_user(args: Namespace) -> None:
    user_store = UserStore(args.bucket_name)
    user_store.delete(args.username)


def parse_args(raw_args: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description='PyPi repository user administrator')
    parser.add_argument('bucket_name', help='PyPi Repository S3 Bucket Name')
    parser.add_argument('-p', '--profile', help='AWS Profile')
    parser.add_argument('-r', '--region', help='AWS Region')

    sp = parser.add_subparsers(dest='command', required=True)
    plist = sp.add_parser('list', help='List Users')
    plist.set_defaults(handler=list_users)

    pset = sp.add_parser('set', help='adds or updates the specified user\'s entry in the user store')
    pset.add_argument('username', help='The name of the user')
    pset.set_defaults(handler=set_user)

    pdel = sp.add_parser('delete', help='delete any entry for the specified user from the user store')
    pdel.add_argument("username", help="the name of the user")
    pdel.set_defaults(handler=del_user)

    return parser.parse_args(raw_args)


def initialize(args: Namespace) -> None:
    if args.profile:
        os.environ["AWS_PROFILE"] = args.profile
    
    if args.region:
        os.environ["AWS_DEFAULT_REGION"] = args.region


def main() -> None:
    args = parse_args(sys.argv[1:])
    initialize(args)

    try:
        args.handler(args)
    except Exception as e:
        print("error: %s" % e)
        sys.exit(1)


if __name__ == '__main__':
    main()
