import json
import sys
from pathlib import Path

import click
import sh
from dotenv import dotenv_values
from rich.console import Console
from rich.padding import Padding
from rich.prompt import Prompt

from ogc import actions, db
from ogc.log import Logger as log
from ogc.spec import SpecLoader

from .base import cli


@click.command()
@click.option("--spec", required=False, multiple=True)
@click.option(
    "--db-file",
    required=False,
    default="ogc-dump.sql",
    help="Filename of the database dump",
)
@click.option(
    "--env-file",
    required=False,
    default="ogc-env.json",
    help="Filename of where to store the OGC environment to be shared",
)
@click.option(
    "--share-public-ssh-key",
    required=False,
    help="The public ssh key from the shared user",
)
def export(spec, db_file, env_file, share_public_ssh_key):
    """Exports the deployment to be shared with other users

    This exports the current database and imports the public ssh key of the
    shared user.

    **Note** on cloud credentials: The credentials must be exported in a `.env` in order
    for the export command to include that information.
    """
    if not sh.which("pg_dump"):
        log.error(f"The pg_dump utility is required to export the database.")
        sys.exit(1)

    # begin setup
    if not share_public_ssh_key:
        share_public_ssh_key = Prompt.ask(
            "Paste the public ssh key of the user you are sharing with"
        )

    log.info("Importing public key to all nodes")
    cmd = f"echo '{share_public_ssh_key}' >> ~/.ssh/authorized_keys"
    results = actions.exec_async(None, None, cmd)
    passed = all(result == True for result in results)
    if passed:
        log.info("Successfully added ssh keys to nodes")
    else:
        log.error("There was an issue importing the ssh keys on some/all nodes.")

    log.info("Exporting database")
    sh.pg_dump(
        "-Fc",
        "-h",
        db.DB_HOST,
        "-p",
        db.DB_PORT,
        "-U",
        db.DB_USER,
        db.DB_NAME,
        _out=db_file,
        _env={"PGPASSWORD": db.DB_PASSWORD},
    )

    specs = SpecLoader.load(list(spec))
    ogc_env_out = {"env": {**dotenv_values(".env")}, "spec": {**specs.as_dict()}}
    Path(env_file).write_text(json.dumps(ogc_env_out))

    console = Console()
    console.print(Padding("Export complete", (2, 0, 0, 0)), justify="center")
    console.print(
        f":: Database Location: [green]{Path(db_file).absolute()}[/]", justify="center"
    )
    console.print(
        f":: Environment: [green]{Path(env_file).absolute()}[/]", justify="center"
    )
    console.print(
        Padding(
            f"Send these files to the user and have them run [green]`ogc import --env-file <file> --db-file <file>`[/]",
            (3, 0, 3, 0),
        ),
        justify="center",
    )


cli.add_command(export)
