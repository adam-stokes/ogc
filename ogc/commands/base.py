import random
import sys
from pathlib import Path

import click
import pkg_resources

from .. import log
from ..enums import SpecCore
from ..spec import SpecJobPlan, SpecLoader
from ..state import app


@click.option(
    "--spec", metavar="<spec>", required=False, multiple=True, help="OGC Spec"
)
@click.option(
    "-t",
    "--tag",
    metavar="<tag>",
    required=False,
    multiple=True,
    help="Only run specific plugin(s) which matches a tag",
)
@click.option("--debug", is_flag=True)
@click.command()
def cli(spec, tag, debug):
    """ Processes a OGC Spec which defines how a build/test/task is performed
    """
    app.debug = debug
    app.log = log

    specs = []
    # Check for local spec
    if Path("ogc.yml").exists() and not spec:
        specs.append(Path("ogc.yml"))

    for sp in spec:
        _path = Path(sp)
        if not _path.exists():
            app.log.error(f"Unable to find spec: {sp}")
            sys.exit(1)
        specs.append(_path)
    app.spec = SpecLoader.load(specs)

    # Handle the plugin loader, initializing the plugin class
    plugins = {
        entry_point.name.lower(): entry_point.load()
        for entry_point in pkg_resources.iter_entry_points("ogc.plugins")
    }
    app.plugins = plugins
    app.jobs = [SpecJobPlan(job) for job in app.spec[SpecCore.PLAN]]

    # randomize jobs for maximum effort
    random.shuffle(app.jobs)

    for job in app.jobs:
        if tag and not set(job.tags).intersection(tag):
            continue

        app.log.info(f"Starting Job: {job.job_id}")
        app.collect.start()
        app.collect.meta()
        job.env()
        if job.condition_if():
            continue
        job.install()
        job.script("before-script")
        job.script("script")
        job.report()
        app.collect.end()
        app.collect.result(job.is_success)
        app.collect.save()
        app.log.info(f"Completed Job: {job.job_id}")

        # This should run after other script sections and reporting is done
        job.script("after-script")

        if job.is_success:
            job.script("deploy")

    if all(job.is_success for job in app.jobs):
        sys.exit(0)
    sys.exit(1)


def start():
    """
    Starts app
    """
    cli()
