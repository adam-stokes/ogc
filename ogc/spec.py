""" spec module
"""

import toml
from flatten_dict import flatten
from dict_deep import deep_get, deep_set
from melddict import MeldDict
from pprint import pformat
from . import log


class SpecLoaderException(Exception):
    pass

class SpecConfigException(Exception):
    """ Raise when a config conflict arises
    """
    pass

class SpecProcessException(Exception):
    """ Raise when process fails
    """
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


class SpecPlugin:
    """ Base plugin class for OGC
    """

    NAME = "SpecPlugin"

    # Options is a list of tuples, (dot.notation.option, True) if required,
    # False if not.
    options = []

    def __init__(self, spec):
        self.spec = spec
        self.spec_options = self.options

    def __str__(self):
        log.info(f"{self.NAME} Specification:\n{pformat(self.spec)}")

    def _dotted_reducer(k1, k2):
        if k1 is None:
            return k2
        else:
            return k1 + "." + k2

    def get_option(self, key):
        try:
            return deep_get(self.spec, key)
        except KeyError:
            return None

    def set_option(self, key, value):
        if key not in self.spec_options:
            raise SpecLoaderException(
                f"Unknown option referenced for {self.NAME}: {key}"
            )
        deep_set(self.spec, key, value)

    def check(self):
        """ Verify options exists
        """
        for key, is_required in self.spec_options:
            try:
                deep_get(self.spec, key)
            except KeyError:
                if is_required:
                    raise SpecLoaderException(
                        f"Attempting to access unknown plugin option for {self.NAME}: {key}"
                    )
        return True

    def conflicts(self):
        """ Handle conflicts between options
        """
        pass

    def process(self):
        """ Process function
        """
        raise NotImplementedError
