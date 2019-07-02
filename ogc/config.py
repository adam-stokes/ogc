""" config module
"""

import toml
from melddict import MeldDict


class ConfigLoaderException(Exception):
    pass


class ConfigLoader(MeldDict):
    def __init__(self):
        super().__init__()

    @classmethod
    def load(cls, configs):
        cl = ConfigLoader()
        for conf in configs:
            cl += toml.loads(conf.read_text())
        return cl

    def to_dict(self):
        return dict(self)
