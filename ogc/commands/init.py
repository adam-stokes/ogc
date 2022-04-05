import json
import os
import sys

import click
from rich.prompt import Prompt
from slugify import slugify

from ogc import db, state
from ogc.log import Logger as log

from .base import ogc as cli

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


@click.command(help="Initialize OGC")
def init():
    db.createtbl(state.app.engine)
    with state.app.session as session:
        has_user = session.query(db.User).first()
        if has_user:
            log.warning("OGC already setup.")
            sys.exit(1)

        # begin setup
        name = Prompt.ask("Enter your name", default=os.environ.get("USER", ""))
        user = db.User(name=name, slug=slugify(name))
        session.add(user)
        session.commit()
    log.info("Setup complete.")


cli.add_command(init)
