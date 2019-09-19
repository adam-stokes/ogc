import importlib
import inspect
import json
import os
import re
import shlex
import signal
import sys
import traceback
import uuid
from pathlib import Path
from subprocess import SubprocessError

import click
import sh
import yaml
from dict_deep import deep_get, deep_set
from dotenv.main import DotEnv
from melddict import MeldDict

from . import log, run
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


class SpecResult:
    """ The result class for a failed task
    """

    def __init__(self, error):
        if not hasattr(error, "full_cmd"):
            self.cmd = "n/a"
            self.code = int(1)
            self.output = str(error)
        else:
            self.cmd = error.full_cmd
            self.code = error.exit_code
            self.output = error.stdout.decode() + error.stderr.decode()
        self.traceback = None

    def set_exception(self, ex):
        tb_lines = traceback.format_exception(ex.__class__, ex, ex.__traceback__)
        self.output = "".join(tb_lines)

    @property
    def is_ok(self):
        return self.code == 0

    @property
    def to_dict(self):
        return {"cmd": self.cmd, "code": self.code, "output": self.output}


class SpecJobPlan:
    """ A Job Plan specification
    """

    def __init__(self, job):
        self.job = job
        self.job_id = str(uuid.uuid4())
        self.results = []
        self.tags = self.job.get("tags", [])
        self.force_shutdown = False
        for sig in [2, 3, 5, 6, 15]:
            signal.signal(sig, self._sighandler)
            app.log.debug(f"Registering signal interupt: {sig}")

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}: running last after-script.")
        self.script("after-script")

    def env(self):
        """ Process env section, these variables will be made available to all
        properties in this job.

        env:
          - SNAP_VERSION=1.15/edge
        """
        _map = {}
        for item in self.job.get("env", []):
            envvars = shlex.split(item)
            for _envvar in envvars:
                app.log.info(f"Adding to env: {_envvar}")
                name, value = _envvar.split("=")
                # env variables set outside of spec take precendence
                if name not in list(os.environ.keys()):
                    _map[name] = value
        app.env += _map

    def install(self):
        """ Processes any install items
        """
        for item in self.job.get("install", []):
            app.log.info(f"Running: {item}")
            try:
                run.script(item, app.env, check=True)
            except SubprocessError as error:
                self.results.append(SpecResult(error))

    def _is_item_plug(self, item):
        """ Check if an item in the spec is referencing a plugin
        """
        if not isinstance(item, dict):
            return False
        plug_name = next(iter(item))
        plug_values = next(iter(item.values()))
        if plug_name not in app.plugins:
            raise SpecProcessException(
                f"Failed to load plugin {plug_name}, make sure "
                f"`ogc-plugins-{plug_name}` is installed."
            )
        return app.plugins[plug_name](plug_values)

    def script(self, key):
        """ Processes before-script, script, and after-script based on key
        """
        for item in self.job.get(key, []):
            plug = self._is_item_plug(item)
            if plug:
                app.log.info(f"Running {key} plugin: {plug.friendly_name}")
                plug.check()
                plug.conflicts()
                try:
                    plug.process()
                except (
                    SpecProcessException,
                    sh.ErrorReturnCode,
                    SubprocessError,
                ) as error:
                    self.results.append(SpecResult(error))
            else:
                app.log.info(f"Running {key}: {item}")
                try:
                    run.script(item, app.env, check=True)
                except (
                    SpecProcessException,
                    sh.ErrorReturnCode,
                    SubprocessError,
                ) as error:
                    self.results.append(SpecResult(error))
        if self.force_shutdown:
            sys.exit(1)

    @property
    def is_success(self):
        """ Returns true/false depending on if job succeeded
        """
        return all(res.code == 0 for res in self.results)

    def report(self):
        # save results
        click.echo("")
        click.echo("")
        if not self.is_success:
            click.secho(f"This job is a FAILURE!\n", fg="red", bold=True)
            app.log.debug("Errors:")
            for res in self.results:
                msg = (
                    f"- Task: {res.cmd}\n- Exit Code: {res.code}\n"
                    f"- Reason:\n{res.output}"
                )
                app.log.debug(msg)
                click.secho(msg, fg="red", bold=True)
        else:
            click.secho(f"This job is a SUCCESS!\n", fg="green", bold=True)

        click.echo("")
        click.echo("")
        report_path = Path(f"{self.job_id}-job.json")
        results_map = [result.to_dict for result in self.results]
        report_path.write_text(json.dumps(results_map))


class SpecPlugin:
    """ Base plugin class for OGC
    """

    friendly_name = "Plugin Specification"

    def __init__(self, spec, options=None):
        """ Load spec

        spec: Plugin specific spec
        specs: Original spec showing all plugins/options
        """
        self.spec = spec
        self.spec_options = options if options else []

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

    def set_option(self, key, value):
        if key not in self.spec_options:
            raise SpecConfigException(
                f"{self.friendly_name} unknown option referenced: {key}"
            )
        deep_set(self.spec, key, value)

    def check(self):
        """ Verify options exists
        """
        for opt in self.spec_options:
            try:
                # Support new option format
                key = opt["key"]
                is_required = opt.get("required", False)
                deep_get(self.spec, key)
            except (KeyError, TypeError):
                if is_required:
                    raise SpecConfigException(f"A required {key} not found, stopping.")

    def conflicts(self):
        """ Handle conflicts between options
        """

    def process(self):
        """ Process function
        """

    @property
    def metadata(self):
        """ Grab plugin metadata
        """
        module_name = Path(inspect.getfile(self.__class__)).stem
        module = importlib.import_module(module_name)
        meta = set(dir(module)).intersection(set(MODULE_METADATA_MAPPING))
        return {key: getattr(module, key) for key in meta}
