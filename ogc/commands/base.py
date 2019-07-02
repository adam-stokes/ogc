from ..config import ConfigLoader, ConfigLoaderException
from ..state import app
from ..debug import debug
from .. import __version__
from pathlib import Path
import click


@click.group()
@click.version_option(__version__)
@click.option("--config", required=False, multiple=True, help="Optional configuration")
def cli(config):
    configs = []
    for conf in config:
        _path = Path(conf)
        if not _path.exists():
            raise ConfigLoaderException("Unable to find config: %s" % conf)
        configs.append(_path)
    app.config = ConfigLoader.load(configs)
    app.debug = debug
