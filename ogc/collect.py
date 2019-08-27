import os
from datetime import datetime
from pathlib import Path

import sh


class Collector:
    """ Provides access to storing persistent information on each run
    """

    def __init__(self):
        self.current_date = datetime.now().strftime("%Y/%m/%d")
        self.current_time = datetime.utcnow().strftime("%H.%M.%S")
        self.db = {"results": []}

    @property
    def path(self):
        """ Returns path of db store
        """
        if os.environ.get("OGC_RESULTS_PATH", None):
            _cache_dir = Path(os.environ.get("OGC_RESULTS_PATH"))
        else:
            _cache_dir = Path.home() / ".local/cache/ogc" / self.current_date
        if not _cache_dir.exists():
            sh.mkdir("-p", str(_cache_dir))
        return _cache_dir / f"{self.current_time}.json"

    def start(self):
        """ Sets a startime timestamp
        """
        self.db["build_datetime"] = str(datetime.utcnow().isoformat())

    def end(self):
        """ Sets a endtime timestamp
        """
        self.db["build_endtime"] = str(datetime.utcnow().isoformat())
