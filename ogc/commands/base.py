from ..spec import SpecLoader, SpecLoaderException, SpecConfigException
from ..state import app
from .. import log
from pathlib import Path
import sys
import click
import pkg_resources
from pprint import pformat


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
    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            app.log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)
    app.spec = SpecLoader.load(specs)

    # Handle the plugin loader, initializing the plugin class
    plugins = {
        entry_point.name: entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("ogc.plugins")
    }

    for plugin in app.spec.keys():
        check_plugin = plugins.get(plugin, None)
        if not check_plugin:
            app.log.debug(f"Skipping plugin {plugin}")
            continue
        app.log.debug(f"Found plugin: {plugin}")

        _specs = app.spec[plugin]
        if not isinstance(_specs, list):
            _specs = [_specs]

        for _spec in _specs:
            runner = check_plugin(_spec)

            # Validate spec is compatible with plugin
            try:
                runner.check()
            except SpecConfigException as error:
                app.log.error(error)
                sys.exit(1)

            app.plugins.append(runner)
