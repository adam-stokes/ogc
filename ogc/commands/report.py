""" Script for generating HTML output
"""

import click
import yaml
from yamlinclude import YamlIncludeConstructor
from pathlib import Path
from .base import cli
from .. import api

YamlIncludeConstructor.add_to_loader_class(loader_class=yaml.Loader)

@click.group()
def report():
    return


@click.command()
@click.option("--template-path", required=True, help="Path to templates directory")
@click.option("--out-path", required=True, help="Path to build output directory")
@click.option(
    "--remote-path",
    required=True,
    help="Remote S3 path, include 's3://' protocol",
    default="s3://jenkaas",
)
@click.option(
    "--report-plan",
    required=True,
    help="YAML describing what the report should process",
    default="report-plan.yaml",
)
def build_validation_report(template_path, out_path, remote_path, report_plan):
    """ Generate a validation report
    """
    plan = Path(report_plan)
    plan = yaml.safe_load(plan.read_text(encoding="utf8"), Loader=yaml.Loader)
    template_path = Path(template_path).absolute()
    out_path = Path(out_path).absolute()
    report = api.report.generate_validation_report(report_plan)
    return api.report.gen_page(
        "index.html", report, str(template_path), str(out_path), remote_path
    )


cli.add_command(report)
report.add_command(build_validation_report)
