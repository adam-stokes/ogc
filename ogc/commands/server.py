import sys

import click

from ogc.celery import app
from ogc.enums import PID_FILE
from ogc.fs import ensure_cache_dir

from .base import cli


@click.command(help="Starts the tasks server")
def server():
    cache_dir = ensure_cache_dir()
    pid_path = cache_dir / PID_FILE
    if not pid_path.exists():
        worker = app.Worker(
            pidfile=str(pid_path), include=["ogc.tasks"], loglevel="INFO"
        )
        worker.start()
    else:
        found_pid = pid_path.read_text().strip()
        click.secho(
            f"OGC Server seems to be already running (pid: {found_pid}). Please verify and remove '{pid_path}' if the process does not exist.",
            fg="red",
        )
        sys.exit(1)


cli.add_command(server)
