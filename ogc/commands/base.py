from ..spec import SpecLoader, SpecLoaderException
from ..state import app
from .. import log, __version__
from pathlib import Path
import click
import pkg_resources


@click.group()
@click.version_option(__version__)
@click.option("--spec", metavar="<spec>", required=False, multiple=True, help="OGC Spec")
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
        entry_point.name: entry_point.load()()
        for entry_point
        in pkg_resources.iter_entry_points('ogc.plugins')
    }
    for plugin in app.spec.keys():
        check_plugin = plugins.get(plugin, None)
        if not check_plugin:
            log.debug(f"Skipping plugin {plugin}")
            continue

        # Process the plugin
        check_plugin.process(app.spec.get(plugin))
