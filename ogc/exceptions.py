class SpecLoaderException(Exception):
    pass


class SpecConfigException(Exception):
    """ Raise when a config conflict arises
    """


class SpecDepException(Exception):
    """ Raise when a dependency conflict arises
    """


class SpecProcessException(Exception):
    """ Raise when process fails
    """
