import os

from argparse import ArgumentParser

parser = ArgumentParser()
parser.add_argument('-a', '--add', help='username:password')
parser.add_argument('-d', '--remove', help='username')
parser.add_argument('-b', '--bucket', help='AWS S3 Bucket', required=True)
parser.add_argument('-p', '--aws_profile', help='AWS CLI Profile', default='default')
parser.add_argument('-r', '--aws_region', help='AWS Region', default='us-east-1')
args = parser.parse_args()

os.environ['AWS_PROFILE'] = args.aws_profile
os.environ['AWS_DEFAULT_REGION'] = args.aws_region

from core.user import S3UserStore

s3UserStore = S3UserStore(
    bucket_name=args.bucket,
    key='config/users'
)

if (args.add):
    username, password, *_ = args.add.split(':')
    s3UserStore.add(username, password)

if (args.remove):
    username, password, *_ = args.remove.split(':')
    s3UserStore.remove(username)
