from kv import KV
from functools import partial
import attr
import box
from datetime import datetime, timedelta
from pathlib import Path
from collections import OrderedDict
from boto3.dynamodb.conditions import Key, Attr
import boto3
import click
import os
import sh
import yaml
from .. import snap, aws, charm
from staticjinja import Site
from string import Template


def generate_days(numdays=30):
    """ Generates last numdays, date range
    """
    base = datetime.today()
    date_list = [
        (base - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(0, numdays)
    ]
    return date_list


def query(name="CIBuilds"):
    """ Scans a table returning results based on our date filters (always 30 days)
    """
    items = []
    dynamodb = aws.DB()
    table = dynamodb.table(name)

    days = generate_days()
    # Required because only 1MB are returned
    # See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.04.html
    response = table.scan()
    for item in response["Items"]:
        try:
            day = datetime.strptime(
                item["build_datetime"], "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%Y-%m-%d")
        except:
            day = datetime.strptime(
                item["build_datetime"], "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d")
        if day not in days:
            continue
        items.append(item)
    while "LastEvaluatedKey" in response:
        response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
        for item in response["Items"]:
            items.append(item)
    return items


def generate_charm_data():
    """ Generates a charm build report
    """
    results = scan_table("CharmBuilds")
    db = OrderedDict()


def generate_data(results, plan):
    """ Generates a report

    plan: report plan
    """

    def _tester(plan, line):
        supported_versions = plan["versions"]
        prefix = plan["prefix"]
        parser = plan["parser"]
        jobs = plan["jobs"]
        parsed_jobs = []
        for version in supported_versions:
            for job in jobs:
                s = Template(parser)
                output = s.substitute(version=version, job=job, prefix=prefix)
                parsed_jobs.append(output)
        return any(line == job for job in parsed_jobs)

    db = OrderedDict()
    metadata = OrderedDict()
    for obj in results:
        obj = box.Box(obj)
        if not _tester(plan, obj.job_name):
            continue
        click.echo(f"Processing {obj.job_name}")
        if obj.job_name not in db:
            db[obj.job_name] = {}

        if "build_datetime" not in obj:
            continue

        if "test_result" not in obj:
            result_bg_class = "bg-light"
        elif not obj["test_result"]:
            result_bg_class = "bg-danger"
        else:
            result_bg_class = "bg-success"

        obj.bg_class = result_bg_class

        try:
            day = datetime.strptime(
                obj["build_datetime"], "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%Y-%m-%d")
        except:
            day = datetime.strptime(
                obj["build_datetime"], "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d")

        if day not in db[obj.job_name]:
            db[obj.job_name][day] = []
        db[obj.job_name][day].append(obj)
    return db


def rows(data):
    days = generate_days()
    rows = []
    for jobname, jobdays in sorted(data.items()):
        sub_item = [jobname]
        for day in days:
            if day in jobdays:
                max_build_number = max(
                    int(item["build_number"]) for item in jobdays[day]
                )
                for job in jobdays[day]:
                    if job["build_number"] == str(max_build_number):
                        sub_item.append(job)
            else:
                sub_item.append({"job_name": jobname, "bg_class": ""})
        rows.append(sub_item)
    return rows


def generate_validation_report(results, plan):
    """ Generate validation report
    """
    metadata = generate_data(results, plan["validation-report"])
    return {
        "rows": rows(metadata),
        "headers": [
            datetime.strptime(day, "%Y-%m-%d").strftime("%m-%d")
            for day in generate_days()
        ],
    }


def generate_validation_addon_report(results, plan):
    """ Generate validation report
    """
    metadata = generate_data(results, plan["validation-addon-report"])
    return {
        "rows": rows(metadata),
        "headers": [
            datetime.strptime(day, "%Y-%m-%d").strftime("%m-%d")
            for day in generate_days()
        ],
    }

def generate_charm_report(plan):
    """ Generate reports on charm manifests
    """
    mapping = {}
    channels = ['stable', 'candidate', 'beta', 'edge']

    for bundle in plan['charm-report']['bundles']:
        bundle_name, data = next(iter(bundle.items()))
        mapping[bundle_name] = {}
        for channel in channels:
            applications = charm.get_bundle_applications(data['namespace'], bundle_name, channel)
            mapping[bundle_name][channel] = {}
            for application, charm_info in applications.items():
                manifest = charm.get_manifest(charm_info['Charm'])
                layers = manifest['layers']
                mapping[bundle_name][channel][application] = [
                     (layer['url'], layer['rev'])
                      for layer in layers
                ]
            click.echo(f"Processing: {bundle_name} - {channel}")
    return {
        "rows": mapping
    }


def gen_pages(
    contexts, template_path, out_path, remote_path="s3://jenkaas", static=None
):
    os.makedirs(out_path, exist_ok=True)
    site = Site.make_site(contexts=contexts, searchpath=template_path, outpath=out_path)
    site.render()
    upload = aws.S3()
    upload.sync_remote(out_path, remote_path)
