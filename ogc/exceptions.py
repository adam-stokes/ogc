from __future__ import annotations


class SpecLoaderException(Exception):
    pass


class SpecProcessException(Exception):
    """Raise when process fails"""


class ProvisionException(Exception):
    """Raise when process fails"""


class ProvisionDeployerException(Exception):
    """Raise when deployer fails"""
