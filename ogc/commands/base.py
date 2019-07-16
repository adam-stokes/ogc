from ..spec import SpecLoader, SpecLoaderException
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
    specs = []
    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            raise SpecLoaderException(f"Unable to find spec: {sp}")
        specs.append(_path)
    app.spec = SpecLoader.load(specs)
    app.debug = debug

    # Handle the plugin loader, initializing the plugin class
    plugins = {
        entry_point.name: entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("ogc.plugins")
    }
    for plugin in app.spec.keys():
        check_plugin = plugins.get(plugin, None)
        if not check_plugin:
            log.debug(f"Skipping plugin {plugin}")
            continue

        runner = check_plugin(app.spec[plugin])

        # Validate spec is compatible with plugin
        if not runner.check():
            # log.error(f"{runner.NAME} has unknown options defined:\n{pformat(runner.spec)}\n{pformat(runner.spec_options)}")
            sys.exit(1)

        app.plugins.append(runner)
