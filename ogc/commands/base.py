# pylint: disable=broad-except

import concurrent.futures
import os
import random
import sys
import tempfile
from pathlib import Path
from pprint import pformat

import click
import pkg_resources

from ..collect import Collector
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

    if not app.spec.get("sequential", False):
        # randomize jobs for maximum effort
        random.shuffle(app.jobs)

    def _run_job(job):
        with tempfile.TemporaryDirectory() as tp:
            os.chdir(tp)
            app.log.info(f"Starting Job: {job.job_id}")
            collect = Collector()
            collect.start(job.job_id)
            collect.meta()
            job.env()
            job.script("pre-execute")
            job.script("execute")
            job.report()
            collect.end()
            collect.result(job.is_success)

            # This should run after other script sections and reporting is done
            job.script("post-execute")

            if job.is_success:
                job.script("deploy")
                job.script("on-success")
            else:
                job.script("on-failure")

            # Collect artifacts
            collect.artifacts()
            collect.push(
                "default", "us-east-1", "jenkaas", "artifacts", ["artifacts.tar.gz"]
            )

            app.log.info("Syncing to database")
            collect.sync_db("default", "us-east-1", "CIBuilds")
            app.log.info(f"Completed Job: {job.job_id}")
            app.log.info("Result:\n{}\n".format(pformat(dict(collect.db))))

    if app.spec.get("concurrent", True):
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as tp:
            jobs = {tp.submit(_run_job, job): job for job in app.jobs}
            for future in concurrent.futures.as_completed(jobs):
                try:
                    future.result()
                except Exception as exc:
                    click.echo(f"Failed thread: {exc}")
    else:
        app.log.info(
            "Running jobs sequentially, concurrency has been disabled for this spec."
        )
        for job in app.jobs:
            _run_job(job)

    if all(job.is_success for job in app.jobs):
        sys.exit(0)
    sys.exit(1)


def start():
    """
    Starts app
    """
    cli()
