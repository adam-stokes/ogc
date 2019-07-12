""" Script for generating HTML output
"""

import click
import yaml
from datetime import datetime
from yamlinclude import YamlIncludeConstructor
from pathlib import Path
from .base import cli
from .. import api

YamlIncludeConstructor.add_to_loader_class(loader_class=yaml.Loader)


@click.group()
def report():
    return


@click.command()
@click.option(
    "--report-plan",
    required=True,
    help="YAML describing what the report should process",
    default="report-plan.yaml",
)
@click.option("--template-path", required=True, help="Path to templates directory")
@click.option("--out-path", required=True, help="Path to build output directory")
@click.option(
    "--remote-path",
    required=True,
    help="Remote S3 path, include 's3://' protocol",
    default="s3://jenkaas",
)
def build_report(report_plan, template_path, out_path, remote_path):
    """ Generate a validation report
    """
    plan = Path(report_plan)
    plan = yaml.load(plan.read_text(encoding="utf8"), Loader=yaml.Loader)
    template_path = Path(template_path).absolute()
    out_path = Path(out_path).absolute()
    data = api.report.query()
    validation_report = api.report.generate_validation_report(data, plan)
    validation_addon_report = api.report.generate_validation_addon_report(data, plan)
    charm_report = api.report.generate_charm_report(plan)
    contexts = [
        (
            "index.html",
            {
                "validate_report": validation_report,
                "validate_addon_report": validation_addon_report,
                "modified": datetime.now(),
            },
        ),
        ("charm_info.html", {"charm_report": charm_report, "modified": datetime.now()}),
    ]
    return api.report.gen_pages(
        contexts, str(template_path), str(out_path), remote_path
    )


cli.add_command(report)
report.add_command(build_report)
