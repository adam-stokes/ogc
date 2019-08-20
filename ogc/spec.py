import importlib
import inspect
import re
from pathlib import Path

import yaml
from dict_deep import deep_get, deep_set
from dotenv.main import DotEnv
from melddict import MeldDict

from . import dep, log
from .enums import MODULE_METADATA_MAPPING
from .state import app


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


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += yaml.safe_load(spec.read_text())
        return cl

    def to_dict(self):
        return dict(self)


class SpecError:
    """ The error class for a failed task
    """

    def __init__(self, plugin, explain, error_code=1):
        self.plugin = plugin
        self.description = self.plugin.opt("description")
        self.explain = explain
        self.error_code = int(error_code)


class SpecPlugin:
    """ Base plugin class for OGC
    """

    friendly_name = "Plugin Specification"

    # Global options applicable to all plugins
    global_options = [
        {"key": "name", "required": False, "description": "Name of runner"},
        {
            "key": "description",
            "required": False,
            "description": "Description of what this runner does",
        },
        {
            "key": "long-description",
            "required": False,
            "description": "An extended description of what this runner does, supports Markdown.",
        },
        {
            "key": "tags",
            "required": False,
            "description": "Global tags to reference during a ogc spec run",
        },
        {
            "key": "deps",
            "required": False,
            "description": "A list of package dependencies needed to run a plugin.",
        },
        {
            "key": "env-requires",
            "required": False,
            "description": "A list of environment variables that must be present for the spec to function.",
        },
        {
            "key": "add-to-env",
            "required": False,
            "description": " ".join(
                [
                    "Convert certain spec options to an environment variable, these variables",
                    "will be set in the host environment in the form of **VAR=VAL**. Note: this",
                    "will convert the dot '.' notation to underscores",
                ]
            ),
        },
        {
            "key": "fail-silently",
            "required": False,
            "description": "Disable exiting on failure, primarily used in conjunction with reporting..",
        },
    ]

    # Options is a list of dictionary of options, descriptions, and requirements
    options = []

    def __init__(self, phase, spec, specs):
        """ Load spec

        phase: Phase this plugin is in
        spec: Plugin specific spec
        specs: Original spec showing all plugins/options
        """
        self.phase = phase
        self.specs = specs
        self.spec = spec
        self.spec_options = self.options

    def __str__(self):
        return log.info(self.friendly_name)

    def _convert_to_env(self, items):
        """ Converts a list of items that may contain $VARNAME into their
        environment variable result. This will return the items unaltered if no
        matches found
        """

        def replace_env(match):
            match = match.group()
            return app.env.get(match[1:])

        _pattern = re.compile(r"\$([_a-zA-Z]+)")
        if isinstance(items, str):
            return re.sub(_pattern, replace_env, items)
        if isinstance(items, bool):
            return items
        if isinstance(items, dict):
            return items
        if isinstance(items, list):
            if all(isinstance(obj, dict) for obj in items):
                return items
            modified = [
                re.sub(_pattern, replace_env, item)
                for item in items
                if isinstance(item, str)
            ]
            return modified
        return items

    def _load_dotenv(self, path):
        if not path.exists():
            return
        _merge_env = DotEnv(dotenv_path=path, encoding="utf8").dict()
        app.env += _merge_env

    def opt(self, key):
        return self.get_plugin_option(key)

    def get_plugin_option(self, key):
        """ Return option defined within a spec plugin
        """
        try:
            val = deep_get(self.spec, key)
            return self._convert_to_env(val)
        except (KeyError, TypeError):
            app.log.debug(f"Option {key} - unavailable, skipping")
            return None

    def spec_opt(self, key):
        return self.get_spec_option(key)

    def get_spec_option(self, key):
        """ Will return an option found in the global spec
        """
        return deep_get(self.specs, key)

    def set_option(self, key, value):
        if key not in self.spec_options:
            raise SpecConfigException(
                f"{self.friendly_name} unknown option referenced: {key}"
            )
        deep_set(self.spec, key, value)

    def check(self):
        """ Verify options exists
        """
        for opt in self.global_options + self.spec_options:
            try:
                # Support new option format
                key = opt["key"]
                is_required = opt.get("required", False)
                log.debug(f"-- verifying {key}, required: {is_required}")
                deep_get(self.spec, key)
            except (KeyError, TypeError):
                if is_required:
                    raise SpecConfigException(
                        f"{self.phase} :: A required {key} not found, stopping."
                    )

        # Check that environment variable requirements are met
        env_requires = self.opt("env-requires")
        if env_requires and any(envvar not in app.env for envvar in env_requires):
            missing_envs = ", ".join(
                sorted(list(set(env_requires).difference(set(app.env))))
            )
            raise SpecConfigException(
                f"{missing_envs} are missing from the required environment variables, please make sure those are loaded prior to running."
            )

    def dep_check(self, show_only=True, install_cmds=False):
        """ Dependency checker

        Arguments:
        show_only: Show a print friendly output of deps from all plugins
        install_cmds: Show the output of install commands for deps that can be passed to sh for automated installs
        sudo: requires install_cmds=True, will show same output just with sudo prepended.
        """

        if show_only and install_cmds:
            raise SpecDepException("Can not have show_only and install_cmd enabled.")

        pkgs = self.opt("deps")
        if not pkgs:
            return []

        if show_only:
            return pkgs

        if install_cmds:
            return [dep.Dep.load(pkg) for pkg in pkgs]

    def env(self):
        """ Setup environment such as adding additional variables to environment

        This can load options from the Env plugin, not required. """
        # Check for a relative .env and load those
        relative_env_path = Path(".") / ".env"
        self._load_dotenv(relative_env_path)
        properties_file = (
            self.opt("properties-file") if "properties-file" in self.spec else None
        )

        if properties_file:
            self._load_dotenv(Path(properties_file))

        # Process any plugin specfic
        extra_env_vars = self.opt("add-to-env") if "add-to-env" in self.spec else None
        env_vars = {}
        if extra_env_vars:
            app.log.debug(f"-- add-to-env set, adding variables.")
            for _var in extra_env_vars:
                try:
                    item_option = self.get_spec_option(_var)
                except KeyError as error:
                    raise SpecProcessException(
                        f"Failed to set an unknown environment variable: {_var}"
                    )
                _var = _var.replace(".", "_").upper()
                env_vars[_var] = item_option
            app.env += env_vars

    def conflicts(self):
        """ Handle conflicts between options
        """

    def process(self):
        """ Process function
        """

    @classmethod
    def doc_plugin_opts(cls):
        """ Returns MD formatted plugin options
        """
        _merge_opts = cls.global_options + cls.options
        rendered = [
            "## Options",
            "",
            "| Option | Required | Description |",
            "|:---    |  :---:   |:---|",
        ]
        for opt in _merge_opts:
            rendered.append(
                f"| {opt['key']} | {opt['required']} | {opt['description']} |"
            )
        return "\n".join(rendered)

    @property
    def metadata(self):
        """ Grab plugin metadata
        """
        module_name = Path(inspect.getfile(self.__class__)).stem
        module = importlib.import_module(module_name)
        meta = set(dir(module)).intersection(set(MODULE_METADATA_MAPPING))
        return {key: getattr(module, key) for key in meta}

    @classmethod
    def doc_example(cls):
        """ Can be overridden in a plugin to provide an example of plugin syntax
        """
        return ""

    @classmethod
    def doc_render(cls):
        """ Renders extra documentation about a plugin if applicable
        """
        return "\n".join(
            [
                f"# {cls.friendly_name}",
                f"## Description\n{str(cls)}",
                "",
                cls.doc_plugin_opts(),
                "",
                cls.doc_example(),
            ]
        )
