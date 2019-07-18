""" spec module
"""

import toml
import os
from pathlib import Path
from dict_deep import deep_get, deep_set
from melddict import MeldDict
from pprint import pformat
from dotenv.main import DotEnv
import click
from . import log, dep
from .state import app


class SpecLoaderException(Exception):
    pass


class SpecConfigException(Exception):
    """ Raise when a config conflict arises
    """

    pass


class SpecDepException(Exception):
    """ Raise when a dependency conflict arises
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

    friendly_name = "SpecPlugin"
    slug = None

    # Options is a list of tuples, (dot.notation.option, True) if required,
    # False if not.
    options = []

    def __init__(self, spec, specs):
        """ Load spec

        spec: Plugin specific spec
        specs: Original spec showing all plugins/options
        """
        self.specs = specs
        self.spec = spec
        self.spec_options = self.options

    def __str__(self):
        return log.info(f"{self.friendly_name} Specification:\n{pformat(self.spec)}")

    def get_option(self, key):
        # TODO: deprecate
        return self.get_plugin_option(key)

    def get_plugin_option(self, key):
        """ Return option defined within a spec plugin
        """
        try:
            return deep_get(self.spec, key)
        except (KeyError) as error:
            log.debug(f"{self.friendly_name} option unset {key}: skipped.")
            return None

    def get_spec_option(self, key):
        """ Will return an option found in the global spec
        """
        try:
            return deep_get(self.specs, key)
        except (KeyError) as error:
            log.debug(f"Spec option unset {key}: skipped.")
            None

    def set_option(self, key, value):
        if key not in self.spec_options:
            raise SpecConfigException(
                f"{self.friendly_name} unknown option referenced: {key}"
            )
        deep_set(self.spec, key, value)

    def check(self):
        """ Verify options exists
        """
        for key, is_required in self.spec_options:
            log.debug(f"Verifying (required: {is_required}) option {key}")
            try:
                return self.get_option(key)
            except (AttributeError, TypeError, KeyError):
                if is_required:
                    raise SpecConfigException(
                        f"Attempting to access unknown plugin option for {self.friendly_name}: {key}"
                    )
        return True

    def _load_dotenv(self, path):
        if not path.exists():
            return
        _merge_env = DotEnv(dotenv_path=path, encoding="utf8").dict()
        app.env += _merge_env

    def dep_check(self, show_only=True, install_cmds=False, sudo=False):
        """ Dependency checker

        Arguments:
        show_only: Show a print friendly output of deps from all plugins
        install_cmds: Show the output of install commands for deps that can be passed to sh for automated installs
        sudo: requires install_cmds=True, will show same output just with sudo prepended.

        This allows each plugin to define dependencies required to run. Take note that this won't actually install the deps for you, however, it does make it easy to install those deps for all loaded plugins:

        [[Runner]]
        name = 'Running a python script'
        executable = 'python3'
        run_script = 'bin/script.py'
        deps = ['apt:python3-pytest', 'pip:pytest-asyncio==5.0.1', 'snap:kubectl/1.15/edge']

        [[Runner]]
        name = 'Running a script'
        run = '''
        #!/bin/bash
        wget http://example.com/zip
        '''
        deps = ['apt:wget']

        To show the required dependencies run:
        > ogc --spec my-run-spec.toml plugin-deps

        Required Dependencies:
        - apt:python3-pytest
        - apt:wget
        - pip:pytest-asyncio==5.0.1
        - snap:kubectl/1.15/edge

        To show the dependencies in a way that can be easily installed for automated runs:
        > ogc --spec my-run-spec.toml plugin-deps --installable
        apt-get install -qyf python3-pytest
        apt-get install -qyf wget
        pip install pytest-asyncio==5.0.1
        snap install kubectl --channel=1.15/edge

        You can optionally pass sudo with it:
        > ogc --spec my-run-spec.toml plugin-deps --installable --with-sudo
        sudo apt-get install -qyf python3-pytest
        sudo apt-get install -qyf wget
        sudo pip install pytest-asyncio==5.0.1
        sudo snap install kubectl --channel=1.15/edge

        You can install them automatically with:
        > ogc --spec my-run-spec.toml plugin-deps --installable --with-sudo | sh -

        Supported formats:
        apt: <package name> Will access apt-get package manager for installation
        pip: <packagename>==<optional version> pip format
        snap: <packagename>/track/channel, snap format, track can be a version like 1.15, channel is stable, candidate, beta, edge.
        """

        if show_only and install_cmds and sudo:
            raise SpecDepException(
                "Can not have show_only, install_cmd and sudo enabled concurrently."
            )
        if show_only and install_cmds:
            raise SpecDepException("Can not have show_only and install_cmd.")

        pkgs = self.get_plugin_option("deps")
        if not pkgs:
            return

        if show_only:
            for pkg in pkgs:
                click.echo(f"  - {pkg}")

        if install_cmds:
            for pkg in pkgs:
                pkg = dep.Dep.load(pkg)
                click.echo(pkg.install_cmd(sudo))

    def env(self):
        """ Setup environment such as adding additional variables to environment

        This can load options from the Env plugin, not required.
        """
        # Check for a relative .env and load thoes
        relative_env_path = Path(".") / ".env"
        self._load_dotenv(relative_env_path)
        properties_file = self.get_option("properties_file")

        if properties_file:
            self._load_dotenv(Path(properties_file))

        # Process any plugin specfic
        extra_env_vars = self.get_plugin_option("add_to_env")
        app.log.debug(f"{self.friendly_name} extra_env_vars - {extra_env_vars}")
        env_vars = {}
        if extra_env_vars:
            app.log.debug(f"{self.friendly_name} add_to_env set, adding variables.")
            for _var in extra_env_vars:
                item_option = self.get_spec_option(_var)
                if not item_option:
                    raise SpecProcessException(
                        f"Failed to set an unknown environment variable: {_var}"
                    )
                _var = _var.replace(".", "_").upper()
                env_vars[_var] = item_option
            app.env += env_vars

    def conflicts(self):
        """ Handle conflicts between options
        """
        pass

    def process(self):
        """ Process function
        """
        pass
