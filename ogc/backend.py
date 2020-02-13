from .backends import juju, lxd


class Backend:
    def __init__(self, backend):
        self._backend = backend

    def create(self):
        """ Based on the type of backend is used, we'll load the appropriate create class
        """
        if self._backend.startswith("juju"):
            return juju.Backend.create()
        elif self._backend.startswith("lxd"):
            return lxd.Backend.create()
