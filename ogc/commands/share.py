import json
import sys
from pathlib import Path

import click
import sh
import yaml
from attr import asdict
from dotenv import dotenv_values
from rich.console import Console
from rich.padding import Padding
from rich.prompt import Prompt

from ogc import actions, enums
from ogc.log import Logger as log
from ogc.spec import SpecLoader

from .base import cli


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
def export_env(spec, db_file, env_file):
    """Exports the deployment to be shared with other users

    This exports the current database and imports the public ssh key of the
    shared user.

    **Note** on cloud credentials: They are not exported and must be set on the shared
    users environment.
    """
    if not sh.which("pg_dump"):
        log.error("The pg_dump utility is required to export the database.")
        sys.exit(1)

    # begin setup
    ssh_key_type = Prompt.ask(
        "How would you like to import the users public ssh key",
        choices=["github", "manual"],
        default="github",
    )

    cmd = None
    if ssh_key_type.lower() == "manual":
        public_ssh_key = Prompt.ask(
            "Paste the public ssh key of the user you are sharing with"
        )
        cmd = f"echo '{public_ssh_key}' >> ~/.ssh/authorized_keys"
    elif ssh_key_type.lower() == "github":
        public_ssh_key = Prompt.ask("Please enter your Github username")
        cmd = (
            f"wget -O get-pip.py https://bootstrap.pypa.io/get-pip.py && "
            "sudo python3 get-pip.py && "
            "sudo pip install ssh-import-id && "
            f"ssh-import-id gh:{public_ssh_key}"
        )
    else:
        log.error("Could not import a public ssh key")
        sys.exit(1)

    log.info("Importing public key to all nodes")
    results = actions.exec_async(None, None, cmd)  # type: ignore
    passed = all(result is True for result in results)
    if passed:
        log.info("Successfully added ssh keys to nodes")
    else:
        log.error("There was an issue importing the ssh keys on some/all nodes.")

    log.info(f"Copying database to: {db_file}")

    _spec = SpecLoader.load(list(spec))
    ogc_env_out = {
        "env": {
            k: v
            for k, v in dotenv_values(".env").items()
            if not any(k.startswith(s) for s in enums.SUPPORTED_PROVIDERS)
        },
        "spec": {**asdict(_spec)},
    }
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
            "Send these files to the user and have them run [green]`ogc import --env-file <file> --db-file <file>`[/]",
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
            "The `createdb` and `psql` utility is required to import the environment."
        )
        sys.exit(1)

    # begin setup
    log.info("Importing data")

    env_data = json.loads(Path(env_file).read_text())
    log.info("Writing environment file")
    env_file_out = Path(".env")
    if env_file_out.exists():
        log.error(
            "The `.env` file exists already, please make a backup and remove that file before importing."
        )
        sys.exit(1)
    with open(env_file_out, "w") as env_f:
        for k, v in env_data["env"].items():
            env_f.write(f"{k.upper()}={v}\n")

    log.info("Writing spec file")
    spec_file_out = Path("ogc.yml")

    with open(spec_file_out, "w") as spec_f:
        spec_f.write(yaml.dump(env_data["spec"]))

    private_ssh_key = Path(private_ssh_key)
    public_ssh_key = Path(public_ssh_key)

    # with state.app.session as s:
    #     for node in s.query(db.Node).all():
    #         node.ssh_public_key = str(public_ssh_key.absolute())
    #         node.ssh_private_key = str(private_ssh_key.absolute())
    #         s.add(node)
    #     s.commit()

    console = Console()
    console.print(Padding("Import complete", (2, 0, 0, 0)), justify="center")
    console.print(":: Database Loaded: [green]:heavy_check_mark:[/]", justify="center")
    console.print(
        ":: Environment Loaded: [green]:heavy_check_mark:[/]", justify="center"
    )
    console.print(
        Padding(
            (
                "Please reference the user guide for interacting with the deployment. "
                "[green]`https://adam-stokes.github.io/ogc/user-guide/managing-nodes`[/]"
            ),
            (3, 0, 3, 0),
        ),
        justify="center",
    )


cli.add_command(import_env)
cli.add_command(export_env)
