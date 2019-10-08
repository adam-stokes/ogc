import json
import os
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
        self.meta_path = Path("metadata.json")

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

    def start(self):
        """ Sets a startime timestamp
        """
        self.db["build_datetime"] = str(datetime.utcnow().isoformat())

    def end(self):
        """ Sets a endtime timestamp
        """
        self.db["build_endtime"] = str(datetime.utcnow().isoformat())

    def result(self, result):
        self.db["test_result"] = bool(result)

    def save(self):
        """ Saves metadata to file
        """
        self.meta_path.write_text(json.dumps(dict(self.db)))
