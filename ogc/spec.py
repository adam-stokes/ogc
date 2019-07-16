""" spec module
"""

import toml
from melddict import MeldDict


class SpecLoaderException(Exception):
    pass


class SpecLoader(MeldDict):
    def __init__(self):
        super().__init__()

    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += toml.loads(spec.read_text())
        return cl

    def to_dict(self):
        return dict(self)
