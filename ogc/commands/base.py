from ..config import ConfigLoader, ConfigLoaderException
from ..state import app
from ..debug import debug
from .. import __version__
from pathlib import Path
import click
import pkg_resources


@click.group()
@click.version_option(__version__)
@click.option("--config", required=False, multiple=True, help="OGC Spec")
def cli(config):
    configs = []
    for conf in config:
        _path = Path(conf)
        if not _path.exists():
            raise ConfigLoaderException(f"Unable to find spec: {conf}")
        configs.append(_path)
    app.config = ConfigLoader.load(configs)
    app.debug = debug

    # Handle the plugin loader, initializing the plugin class
    plugins = {
        entry_point.name: entry_point.load()()
        for entry_point
        in pkg_resources.iter_entry_points('ogc.plugins')
    }
    for plugin in app.config.keys():
        click.echo(f"Loading {plugin}")
