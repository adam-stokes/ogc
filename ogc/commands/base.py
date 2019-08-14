import sys
from pathlib import Path

import click
import pkg_resources

from .. import log
from ..enums import SPEC_CORE_PLUGINS, SPEC_PHASES
from ..spec import SpecConfigException, SpecLoader
from ..state import app


@click.group()
@click.option(
    "--spec", metavar="<spec>", required=False, multiple=True, help="OGC Spec"
)
@click.option("--debug", is_flag=True)
def cli(spec, debug):
    """ Processes a OGC Spec which defines how a build/test/task is performed
    """
    app.debug = debug
    app.log = log

    specs = []
    # Check for local spec
    if Path("ogc.yml").exists() and not spec:
        specs.append(Path("ogc.yml"))

    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            app.log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)
    app.spec = SpecLoader.load(specs)

    # Handle the plugin loader, initializing the plugin class
    plugins = {
        entry_point.name.lower(): entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("ogc.plugins")
    }

    for phase in app.spec.keys():
        if phase in SPEC_CORE_PLUGINS:
            continue
        if phase not in SPEC_PHASES:
            app.log.error(
                f"`{phase}` is an incorrect phase for this spec, please review the specfile."
            )
            sys.exit(1)

        for plugin in app.spec[phase]:
            check_plugin = plugins.get(next(iter(plugin)), None)
            if not check_plugin:
                app.log.debug(
                    f"Could not find plugin {next(iter(plugin)).lower()}, install with `pip install ogc-plugins-{next(iter(plugin)).lower()}`"
                )
                continue

            runner = check_plugin(phase, next(iter(plugin.values())), app.spec)
            if runner.opt("description"):
                _desc = runner.opt("description")
            else:
                setattr(
                    runner.__class__,
                    "__str__",
                    lambda x: "A Plugin, please add a __str__ attribute for a plugin description.",
                )
                _desc = str(runner)
            app.log.debug(f"{phase} :: loaded : {_desc}")

            # Validate spec is compatible with plugin
            try:
                runner.check()
            except SpecConfigException as error:
                app.log.error(error)
                sys.exit(1)

            app.phases[phase].append(runner)

            # This is to keep a definitive list of all plugins across all phases.
            app.plugins.append(runner)


def start():
    """
    Starts app
    """
    cli()
