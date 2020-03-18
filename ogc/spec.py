import importlib
import inspect
import itertools
import json
import os
import re
import shlex
import signal
import sys
import tempfile
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
from yamlinclude import YamlIncludeConstructor

from . import log, run
from .enums import MODULE_METADATA_MAPPING
from .exceptions import SpecConfigException, SpecProcessException
from .state import app

YamlIncludeConstructor.add_to_loader_class(
    loader_class=yaml.FullLoader, base_dir=str(Path.cwd())
)


def _convert_to_env(items):
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


class SpecLoader(MeldDict):
    @classmethod
    def load(cls, specs):
        cl = SpecLoader()
        for spec in specs:
            cl += yaml.load(spec.read_text(), Loader=yaml.FullLoader)
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


class SpecJobMatrix:
    """ Job matrix
    """

    def __init__(self, matrix):
        self.matrix = matrix

    def generate(self):
        """ Generates the build combinations
        """
        all_names = sorted(self.matrix)
        combos = itertools.product(*(self.matrix[item] for item in all_names))
        combo_map = []
        for line in combos:
            combine = zip(all_names, line)
            combo_map.append({a: b for a, b in combine})
        return combo_map


class SpecJobPlan:
    """ A Job Plan specification
    """

    def __init__(self, job, matrix):
        self.job = job
        self.workdir = tempfile.mkdtemp()
        self.matrix = matrix
        self.job_id = str(uuid.uuid4())
        self.results = []
        self.tags = self.job.get("tags", [])
        self.force_shutdown = False
        for sig in [1, 2, 3, 5, 6, 15]:
            signal.signal(sig, self._sighandler)
            app.log.debug(f"Registering signal interupt: {sig}")

    def _sighandler(self, sig, frame):
        self.force_shutdown = True
        app.log.debug(f"Caught signal {sig} - {frame}: running last after-script.")
        self.script("post-execute")

    def cleanup(self):
        run.cmd_ok(f"rm -rf {self.workdir}", shell=True)

    def env(self):
        """ Process env section, these variables will be made available to all
        properties in this job.

        env:
          - SNAP_VERSION=1.15/edge
        """
        _map = {}

        # Process our matrix items first as env so that future env setup can pull from those values if needed
        for name, value in self.matrix.items():
            app.env[name.upper()] = value

        for item in self.job.get("env", []):
            envvars = shlex.split(item)
            for _envvar in envvars:
                name, value = _envvar.split("=")
                value = _convert_to_env(value)
                # env variables set outside of spec take precendence
                _value = os.environ.get(name, value)
                _map[name] = _value
                app.log.info(f"ENV: {name}={_value}")
        app.env += _map
        app.env["OGC_JOB_ID"] = self.job_id
        app.env["OGC_JOB_WORKDIR"] = self.workdir

    def condition_if(self):
        """ Processes any conditional items

        This will determine if the job should run or not based on a failed or
        pass state. If the condition fails (an exit code other than 0) this job
        will be set to execute, otherwise a passing test will skip job. All
        items in this section should pass or fail there is no mix of the 2.
        """
        if "if" not in self.job:
            return True

        try:
            item = self.job.get("if", "exit 0")
            app.log.info(f"Checking conditional:\n {item}")
            run.script(item, app.env)
        except SpecProcessException as error:
            return False
        return True

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
        item = self.job.get(key, None)
        if item:
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
                app.log.info(f"Running {key}:\n{item}")
                try:
                    run.script(item, app.env)
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
        if all(res.code == 0 for res in self.results):
            return 1
        return 0

    def report(self):
        # save results
        click.echo("")
        click.echo("")
        if not self.is_success:
            click.secho(
                f"This job is a FAILURE ({self.is_success})!\n", fg="red", bold=True
            )
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
        report_path = Path(f"{self.workdir}/results-{self.job_id}.json")
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
            return _convert_to_env(val)
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
