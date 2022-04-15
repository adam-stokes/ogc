import os
import sys

import click
from rich.prompt import Prompt

from ogc import db, models
from ogc.log import Logger as log

from .base import cli


@click.command(help="Initialize OGC")
def init():
    # begin setup
    name = Prompt.ask("Enter your name", default=os.environ.get("USER", ""))
    user = models.User(name=name)
    with db.get().begin(write=True) as txn:
        if txn.get(user.slug.encode("ascii")):
            log.warning("OGC already setup.")
            sys.exit(1)
        txn.put(user.slug.encode("ascii"), db.model_as_pickle(user))
    log.info("Setup complete.")


cli.add_command(init)
