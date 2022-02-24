import re
import os
import sys
import shutil

from typing import Sequence
from jinja2 import Environment
from core.utils import get_path
from core.storage import Storage
from subprocess import check_output
from collections import defaultdict
from argparse import ArgumentParser, Namespace


class Package:

    def __init__(self, name: str, files) -> None:
        self.name, self.version = name.rsplit("-", 1)
        self.files = set(files)

    @staticmethod
    def create(dist_path: str = 'dist', use: str = None):
        name = None
        files = []

        dist_path = get_path(dist_path)
        if os.path.exists(dist_path):
            shutil.rmtree(dist_path)

        if use == 'poetry':
            output = check_output(['poetry', 'build']).decode().strip()
            for file in filter(lambda o: o.startswith('  - Built '), output.split('\n')):
                file = file.replace('  - Built ', '')
                files.append(file)
                if file.endswith('.tar.gz'):
                    name = file[:-7]
        else:
            pass

        return Package(name, files)


class IndexTemplate:

    TEMPLATE = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Package Index</title>
    </head>
    <body>
    {{%- for package in packages | sort -%}}
        {{%- for filename in package.files | sort %}}
        <a href="{{{{ filename | urlencode }}}}">{{{{ filename }}}}</a><br>
        {{%- endfor -%}}
    {{%- endfor %}}
    </body>
    </html>
    """

    def __init__(self, packages):
        self.packages = set(packages)
        self.template = Environment().from_string(self.TEMPLATE)

    @staticmethod
    def parse(html):
        filenames = defaultdict(set)

        for match in re.findall(
            r'<a href=".+">((.+?-((?:\d+!)?\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?(?:\.post\d+)?'
            + r"(?:\.dev\d+)?)(?:\+([a-zA-Z0-9\.]+))?).*(?:\.whl|\.tar\.gz))</a>",
            html,
        ):
            filenames[match[1]].add(match[0])
        return IndexTemplate(Package(name, files) for name, files in filenames.items())

    def to_html(self):
        return self.template.render({'packages': self.packages})

    def add_package(self, package):
        if any(p.version == package.version for p in self.packages):
            raise Exception("%s already exists! You should use a different version." % package)
        self.packages.add(package)


def create_and_update_package(args: Namespace) -> None:
    package = Package.create(args.dist_path, args.use)
    storage = Storage(args.bucket_name, f'{package.name}/index.html')

    index = IndexTemplate.parse(storage.get_index())
    index.add_package(package)

    storage.upload_package(package, args.dist_path)
    storage.upload_index(index.to_html())


def parse_args(raw_args: Sequence[str]) -> Namespace:
    parser = ArgumentParser(description='PyPi repository user administrator')
    parser.add_argument('bucket_name', help='PyPi Repository S3 Bucket Name')
    parser.add_argument('-d', '--dist_path', default='dist', help='Path to directory with wheel/sdist to be uploaded')
    parser.add_argument('-p', '--profile', help='AWS Profile')
    parser.add_argument('-r', '--region', help='AWS Region')
    parser.add_argument('-u', '--use', choices=['poetry'], help='Use package manager [poetry]')
    parser.set_defaults(handler=create_and_update_package)
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
