import os
import sys

import click
from rich.prompt import Prompt

from ogc import models
from ogc.db import M, model_as_pickle
from ogc.log import Logger as log

from .base import cli


@click.command(help="Initialize OGC")
def init():
    # begin setup
    name = Prompt.ask("Enter your name", default=os.environ.get("USER", ""))
    user = models.User(name=name)
    with M.db.begin(write=True) as txn:
        if txn.get(user.slug.encode("ascii")):
            log.warning("OGC already setup.")
            sys.exit(1)
        txn.put(user.slug.encode("ascii"), model_as_pickle(user))
    log.info("Setup complete.")


cli.add_command(init)
