import json
import sys
from pathlib import Path

import click
import sh
import yaml
from dotenv import dotenv_values
from rich.console import Console
from rich.padding import Padding
from rich.prompt import Prompt

from ogc import actions, db, state
from ogc.log import Logger as log
from ogc.spec import SpecLoader

from .base import cli

if not state.app.engine:
    state.app.engine = db.connect()
    state.app.session = db.session(state.app.engine)


@click.command()
@click.option(
    "--spec",
    required=False,
    multiple=True,
    help="Location of the ogc.yml or other spec files to include in export",
)
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
    "--public-ssh-key",
    required=False,
    help="The public ssh key contents from the shared user",
)
def export_env(spec, db_file, env_file, public_ssh_key):
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
    if not public_ssh_key:
        public_ssh_key = Prompt.ask(
            "Paste the public ssh key of the user you are sharing with"
        )

    log.info("Importing public key to all nodes")
    cmd = f"echo '{public_ssh_key}' >> ~/.ssh/authorized_keys"
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


@click.command()
@click.option(
    "--db-file",
    required=True,
    default="ogc-dump.sql",
    help="Filename of the database dump",
)
@click.option(
    "--env-file",
    required=True,
    default="ogc-env.json",
    help="Filename of where to store the OGC environment to be shared",
)
@click.option(
    "--private-ssh-key",
    required=True,
    help="The path to your private ssh key. This must match the public ssh key used during the export.",
)
@click.option(
    "--public-ssh-key",
    required=True,
    help="The path to your public ssh key. This must match the ssh key used during the export.",
)
def import_env(db_file, env_file, private_ssh_key, public_ssh_key):
    """Imports a shared deployment"""
    if not sh.which("createdb") and not sh.which("psql"):
        log.error(
            f"The `createdb` and `psql` utility is required to import the environment."
        )
        sys.exit(1)

    # begin setup
    log.info("Creating database")
    try:
        sh.createdb(
            "-h",
            db.DB_HOST,
            "-p",
            db.DB_PORT,
            "-U",
            db.DB_USER,
            db.DB_NAME,
            _env={"PGPASSWORD": db.DB_PASSWORD},
        )
    except sh.ErrorReturnCode as e:
        log.error(e)
        sys.exit(1)

    log.info("Importing data")
    try:
        sh.psql(
            "-h",
            db.DB_HOST,
            "-p",
            db.DB_PORT,
            "-U",
            db.DB_USER,
            "-d",
            db.DB_NAME,
            "-f",
            db_file,
            _env={"PGPASSWORD": db.DB_PASSWORD},
        )
    except sh.ErrorReturnCode as e:
        log.error(e)
        sys.exit(1)

    env_data = json.loads(Path(env_file).read_text())
    log.info("Writing spec file")
    env_file_out = Path(".env")
    with open(env_file_out, "w") as env_f:
        for k, v in env_data["env"].items():
            env_f.write(f"{k.upper()}={v}")

    spec_file_out = Path("ogc.yml")

    with open(spec_file_out, "w") as spec_f:
        spec_f.write(yaml.dumps(env_data["spec"]))

    private_ssh_key = Path(private_ssh_key)
    public_ssh_key = Path(public_ssh_key)

    with state.app.session as s:
        for node in s.query(db.Node).all():
            node.ssh_public_key = str(public_ssh_key.absolute())
            node.ssh_private_key = str(private_ssh_key.absolute())

    console = Console()
    console.print(Padding("Import complete", (2, 0, 0, 0)), justify="center")
    console.print(f":: Database Loaded: [green]:heavy_check_mark:[/]", justify="center")
    console.print(
        f":: Environment Loaded: [green]:heavy_check_mark:[/]", justify="center"
    )
    console.print(
        Padding(
            f"Please reference the user guide for interacting with the deployment. [green]`https://adam-stokes.github.io/ogc/user-guide/managing-nodes`[/]",
            (3, 0, 3, 0),
        ),
        justify="center",
    )


cli.add_command(import_env)
cli.add_command(export_env)
