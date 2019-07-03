""" helpful aws utilities
"""

import boto3
import sh


class AWSSession:
    def __init__(self, region="us-east-1"):
        self.session = boto3.Session(region_name=region)


class DB:
    def __init__(self, region="us-east-1"):
        self.dynamodb = AWSSession(region).session.resource("dynamodb")

    def table(self, name):
        return self.dynamodb.Table(name)


class S3:
    def __init__(self, region="us-east-1", bucket="jenkaas"):
        self.s3 = AWSSession(region).session.resource("s3")
        self.bucket = self.s3.Bucket(bucket)

    def sync_remote(self, src, dst):
        """ Syncs directories to remote s3 location

        src: local directory, ie reports/_build
        dst: s3 destination, ie s3://jenkaas
        """
        sh.aws.s3.sync(src, dst)
