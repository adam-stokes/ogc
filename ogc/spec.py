"""
---
targets: ['docs/plugins/spec.md']
---

# Plugin specification

## Built-in Methods

**def:check** - Runs a preliminary check making sure options specified in a spec file exist in the plugin.

**def:dep_check** - Parse and print out install commands for plugin dependencies such as apt, snap, and pip.

This allows each plugin to define dependencies required to run. Take note that
this won't actually install the plugin deps for you, however, it does make it easy to
install those deps for all loaded plugins:

Current Supported formats:

| Type | Args | Description | Example |
| :--- | :--: | :---        | :---    |
| apt  | PKG_NAME |  Will access apt-get package manager for installation | apt:python3-test
| pip  | PKG_NAME>=PIP_VERSION | pip format | pip:black>=0.10.0,<1.0.0 |
| snap | PKG_NAME/track/channel | snap format, track can be a version like 1.15, channel is stable, candidate, beta, edge.| snap:kubectl/1.15/edge:classic |

A plugin dependency can be in the following form:

```toml
[[Runner]]
deps = ['apt:python3-pytest', 'pip:pytest-asyncio==5.0.1', 'snap:kubectl/1.15/edge:classic']
```

A user can then get that information prior to running so that all requirements are met.

```
> ogc --spec my-run-spec.toml plugin-deps
```

**Returns**:

```
Required Dependencies:
  - apt:python3-pytest
  - apt:wget
  - pip:pytest-asyncio==5.0.1
  - snap:kubectl/1.15/edge
```

To show the dependencies in a way that can be easily installed for automated runs:

```
> ogc --spec my-run-spec.toml plugin-deps --installable
```

**Returns**:

```
sudo apt-get install -qyf python3-pytest
sudo apt-get install -qyf wget
pip install --user pytest-asyncio==5.0.1
snap install kubectl --channel=1.15/edge
```

You can install them automatically with:
```
> ogc --spec my-run-spec.toml plugin-deps --installable --with-sudo | sh -
```

**def:env** - Will read and set host environment variables, along with any DotEnv
  specified one or if a properties_file is found (Which uses the Env plugin
  itself for that.) Environment variables are merge left, updating any existing
  key:val pairs found.

## Not implemented methods

These methods must be defined in the plugin itself as these are not implemented at the spec level.

**def:conflicts** - Useful if there are certain plugin options that can not be run together. Should be overridden in the plugin.

**def:process** - Process the plugin, this handles the majority of the plugin's execution task. Should be overridden in the plugin.
"""

import toml
import os
import re
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

    friendly_name = "Plugin Specification"
    description = "The reference architecture of a plugin"
    slug = None

    # Global options applicable to all plugins
    global_options = [
        {"key": "name", "required": True, "description": "Name of runner"},
        {
            "key": "description",
            "required": True,
            "description": "Description of what this runner does",
        },
        {
            "key": "long_description",
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
            "key": "env_requires",
            "required": False,
            "description": "A list of environment variables that must be present for the spec to function.",
        },
        {
            "key": "add_to_env",
            "required": False,
            "description": " ".join(
                [
                    "Convert certain spec options to an environment variable, these variables",
                    "will be set in the host environment in the form of **VAR=VAL**. Note: this",
                    "will convert the dot '.' notation to underscores",
                ]
            ),
        },
    ]

    # Options is a list of dictionary of options, descriptions, and requirements
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

    def _convert_to_env(self, items):
        """ Converts a list of items that may contain $VARNAME into their
        environment variable result. This will return the items unaltered if no matches found
        """

        def replace_env(match):
            match = match.group()
            return app.env.get(match[1:])

        updated_items = []
        _pattern = re.compile(r"\$([_a-zA-Z]+)")
        if items is None:
            items = []
        if isinstance(items, str):
            items = [items]
        return [re.sub(_pattern, replace_env, item) for item in items]

    def _load_dotenv(self, path):
        if not path.exists():
            return
        _merge_env = DotEnv(dotenv_path=path, encoding="utf8").dict()
        app.env += _merge_env

    def get_plugin_option(self, key):
        """ Return option defined within a spec plugin
        """
        try:
            val = deep_get(self.spec, key)
            result = self._convert_to_env(val)
            if len(result) == 1:
                return result[0]
            return result
        except (KeyError, TypeError) as error:
            app.log.debug(f"Option {key} unavailable: {error}")
            return None

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
            except (KeyError, TypeError) as error:
                if is_required:
                    raise SpecConfigException(f"A required {key} not found, stopping.")
        return

    def dep_check(self, show_only=True, install_cmds=False, sudo=False):
        """ Dependency checker

        Arguments:
        show_only: Show a print friendly output of deps from all plugins
        install_cmds: Show the output of install commands for deps that can be passed to sh for automated installs
        sudo: requires install_cmds=True, will show same output just with sudo prepended.
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
        properties_file = (
            self.get_plugin_option("properties_file")
            if "properties_file" in self.spec
            else None
        )

        if properties_file:
            self._load_dotenv(Path(properties_file))

        # Process any plugin specfic
        extra_env_vars = (
            self.get_plugin_option("add_to_env") if "add_to_env" in self.spec else None
        )
        env_vars = {}
        if extra_env_vars:
            app.log.debug(f"-- add_to_env set, adding variables.")
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
        pass

    def process(self):
        """ Process function
        """
        pass

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
                f"## Description\n{cls.description}",
                "",
                cls.doc_plugin_opts(),
                "",
                cls.doc_example(),
            ]
        )
