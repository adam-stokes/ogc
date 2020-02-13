import sys
from pathlib import Path

import click
import pkg_resources

from ..enums import SpecCore
from ..spec import SpecJobMatrix, SpecJobPlan, SpecLoader
from ..state import app


@click.option(
    "--spec", metavar="<spec>", required=False, multiple=True, help="OGC Spec"
)
@click.option("--debug", is_flag=True)
@click.command()
def cli(spec, debug):
    """ Processes a OGC Spec which defines how a build/test/task is performed
    """
    app.debug = debug

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

    matrixes = SpecJobMatrix(app.spec[SpecCore.MATRIX])
    app.jobs = [
        SpecJobPlan(app.spec[SpecCore.PLAN], matrix) for matrix in matrixes.generate()
    ]

    for job in app.jobs:
        app.log.info(f"Starting Job: {job.job_id}")
        app.collect.start(job.job_id)
        app.collect.meta()
        job.env()
        job.script("pre-execute")
        job.script("execute")
        job.report()
        app.collect.end()
        app.collect.result(job.is_success)
        app.collect.save()
        app.log.info(f"Completed Job: {job.job_id}")

        # This should run after other script sections and reporting is done
        job.script("post-execute")

        if job.is_success:
            job.script("deploy")
            job.script("on-success")
        else:
            job.script("on-failure")

    if all(job.is_success for job in app.jobs):
        sys.exit(0)
    sys.exit(1)


def start():
    """
    Starts app
    """
    cli()
