import os
from pathlib import Path

import dill


class Cache:
    def __init__(self):
        self.cache_dir = Path(__file__).cwd() / ".ogc-cache"
        if not self.cache_dir.exists():
            os.makedirs(str(self.cache_dir))

    @property
    def inventory(self):
        """Returns list of known inventory"""
        metadata = {}
        for fname in os.listdir(str(self.cache_dir)):
            metadata[fname.replace("-", "-")] = self.load(fname)
        return metadata

    def save(self, fname, attrs):
        meta_file = self.cache_dir / fname
        meta_file.write_bytes(dill.dumps(attrs))

    def load(self, fname):
        meta_file = self.cache_dir / fname
        return dill.loads(meta_file.read_bytes())

    def exists(self, fname):
        meta_file = self.cache_dir / fname
        return meta_file.exists()

    def delete(self, fname):
        meta_file = self.cache_dir / fname
        os.remove(str(meta_file))
