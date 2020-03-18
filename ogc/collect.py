import json
import operator
import os
from datetime import datetime
from pathlib import Path

from loguru import logger

from .run import cmd_ok
from .state import app


class Collector:
    """ Provides access to storing persistent information on each run
    """

    def __init__(self, job_id, workdir):
        self.current_date = datetime.now().strftime("%Y/%m/%d")
        self.current_time = datetime.utcnow().strftime("%H.%M.%S")
        self.workdir = workdir
        self.job_id = job_id

    def meta(self):
        """ Sets metadata information
        """
        env = os.environ.copy()
        self.setk("job_name", env.get("JOB_NAME", "yoink"))
        self.setk("build_number", env.get("BUILD_NUMBER", 0))
        self.setk("build_tag", env.get("BUILD_TAG", "master"))
        self.setk("workspace", env.get("WORKSPACE", "n/a"))
        self.setk("git_commit", env.get("GIT_COMMIT", "n/a"))
        self.setk("git_url", env.get("GIT_URL", "n/a"))
        self.setk("git_branch", env.get("GIT_BRANCH", "master"))

    def start(self):
        """ Sets a startime timestamp
        """
        logger.add(f"{self.workdir}/job-{self.job_id}.log", rotation="5 MB", level="DEBUG")
        self.setk("build_datetime", str(datetime.utcnow().isoformat()))
        self.setk("job_id", self.job_id)

    def end(self):
        """ Sets a endtime timestamp
        """
        self.setk("build_endtime", str(datetime.utcnow().isoformat()))

    def setk(self, db_key, db_val):
        """ Sets arbitrary db key/val
        """
        app.redis.hset(self.job_id, db_key, db_val)

    def getk(self, db_key):
        """ Gets db key/val
        """
        val = app.redis.hget(self.job_id, db_key)
        return val

    def artifacts(self):
        """ Tars up any artifacts in the job directory
        """
        cmd_ok(f"tar cvzf {self.workdir}/artifacts.tar.gz {self.workdir}/*", shell=True)

    def push(self, profile_name, region_name, bucket, db_key, files):
        """ Pushes files to s3, needs AWS configured prior
        """
        import boto3

        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        s3 = session.client("s3")
        result_path_objs = []
        for r_file in files:
            r_file = Path(r_file)
            if not r_file.exists():
                continue
            result_path_objs.append((r_file, r_file.stat().st_mtime))

        newest_result_file = max(result_path_objs, key=operator.itemgetter(1))[0]
        current_date = datetime.now().strftime("%Y/%m/%d")
        s3_path = Path(str(self.job_id)) / newest_result_file.parts[-1]
        s3.upload_file(str(newest_result_file), bucket, str(s3_path))
        self.setk(db_key, str(s3_path))

    def result(self, result):
        self.setk("test_result", result)

    def sync_db(self, profile_name, region_name, table):
        """ syncs to dynamo
        """
        import boto3

        session = boto3.Session(profile_name=profile_name, region_name=region_name)
        dynamodb = session.resource("dynamodb")
        table = dynamodb.Table(table)
        table.put_item(Item=dict(app.redis.hgetall(self.job_id)))

    def to_json(self):
        """ Write metadata to json
        """
        Path(f"{self.workdir}/metadata-{self.job_id}.json").write_text(json.dumps(dict(app.redis.hgetall(self.job_id))))
