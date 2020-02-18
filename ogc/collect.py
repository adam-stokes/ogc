import os
import click
from datetime import datetime
from pathlib import Path
from kv import KV


class Collector:
    """ Provides access to storing persistent information on each run
    """

    def __init__(self):
        self.current_date = datetime.now().strftime("%Y/%m/%d")
        self.current_time = datetime.utcnow().strftime("%H.%M.%S")
        self.db = KV("metadata.db")

    def meta(self):
        """ Sets metadata information
        """
        env = os.environ.copy()
        self.db["job_name"] = env.get("JOB_NAME", "yoink")
        self.db["build_number"] = env.get("BUILD_NUMBER", 0)
        self.db["build_tag"] = env.get("BUILD_TAG", "master")
        self.db["workspace"] = env.get("WORKSPACE", "n/a")
        self.db["git_commit"] = env.get("GIT_COMMIT", "n/a")
        self.db["git_url"] = env.get("GIT_URL", "n/a")
        self.db["git_branch"] = env.get("GIT_BRANCH", "master")

    def start(self, job_id):
        """ Sets a startime timestamp
        """
        self.db["build_datetime"] = str(datetime.utcnow().isoformat())
        self.db["job_id"] = job_id

    def end(self):
        """ Sets a endtime timestamp
        """
        self.db["build_endtime"] = str(datetime.utcnow().isoformat())

    def setk(self, db_key, db_val):
        """ Sets arbitrary db key/val
        """
        self.db[db_key] = db_val

    def getk(self, db_key):
        """ Gets db key/val
        """
        val = self.db.get(db_key, "")
        return val

    def result(self, result):
        self.db["test_result"] = bool(result)
