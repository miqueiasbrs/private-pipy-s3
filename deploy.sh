#!/bin/bash
BUCKET_NAME=$1
DOMAIN_NAME=$2
REPOSITORY_NAME=$3
CERTIFICATE_ARN=$4
CODEBUILD_SRC_DIR=$PWD

if [ -z "$1" ]
then
    echo "Bucket Name is required"
    exit 0
fi

if [ -z "$2" ]
then
    echo "Domain name is required"
    exit 0
fi

if [ -z "$3" ]
then
    echo "S3 Bucket repository name is required"
    exit 0
fi

if [ -z "$4" ]
then
    echo "AWS CA arn is required"
    exit 0
fi

rm -rf $CODEBUILD_SRC_DIR/app.zip
rm -rf $CODEBUILD_SRC_DIR/.venv
rm -rf $CODEBUILD_SRC_DIR/poetry.lock

find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf

echo "================= DOWNLOADING DEPENDENCIES ================="
poetry install --no-dev
echo "====================== BUILD PACKAGES ======================"
zip -r9 $CODEBUILD_SRC_DIR/app.zip pyproject.toml
cd $CODEBUILD_SRC_DIR/.venv/lib/*/site-packages
zip -ru9 $CODEBUILD_SRC_DIR/app.zip . -x '*__pycache__/*' '*_distutils_hack/*' '*pip*' '*pkg_resources/*' '*setuptools*' '*wheel*' '*_virtualenv*' '*distutils-precedence*' '*.dist-info*'
cd $CODEBUILD_SRC_DIR/aws-pypi-s3
zip -ru9 $CODEBUILD_SRC_DIR/app.zip . -x '*.venv*' '*.env*' '*poetry.lock*' '*__pycache__/*' '*.vscode/*' '*manage.py*' '*htmlcov/*' '*.pytest_cache/*' '*tests/*'
cd $CODEBUILD_SRC_DIR
echo "========================== UPLOAD =========================="
aws s3 cp $CODEBUILD_SRC_DIR/app.zip s3://$BUCKET_NAME/aws-pypi-s3/app.zip --profile lets-dev2 --region us-east-1
aws s3api list-object-versions --bucket $BUCKET_NAME --prefix aws-pypi-s3/app.zip --max-items 1 --profile lets-dev2 --region us-east-1 > artifactVersion.json

aws cloudformation deploy --template-file pypi.yml --stack-name pypi \
     --parameter-overrides ArtifactBucket=$BUCKET_NAME \
     ArtifactPackage=aws-pypi-s3/app.zip \
     ArtifactPackageVersion=$(python -c "import json;print(json.loads(open('artifactVersion.json', 'r').read())['Versions'][0]['VersionId'])") \
     PyPiRepositoryName=$3 \
     PyPiDomainName=$2 \
     AcmCertificateArn=$4 \
     --capabilities CAPABILITY_NAMED_IAM CAPABILITY_NAMED_IAM --profile lets-dev2 --region us-east-1
