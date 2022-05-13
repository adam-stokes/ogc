import os
import sys

import click
from rich.prompt import Prompt

from ogc import models
from ogc.db import M
from ogc.log import Logger as log

from .base import cli


@click.command(help="Initialize OGC")
def init() -> None:
    # begin setup
    name = Prompt.ask("Enter your name", default=os.environ.get("USER", ""))
    new_user = models.User(name=name)
    M.save(new_user.slug, new_user)
    log.info(f"Setup complete for `{new_user.name}`.")


cli.add_command(init)
