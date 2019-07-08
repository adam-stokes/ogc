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
from .. import snap, aws
from staticjinja import Site


def generate_days(numdays=30):
    """ Generates last numdays, date range
    """
    base = datetime.today()
    date_list = [
        (base - timedelta(days=x)).strftime("%Y-%m-%d") for x in range(0, numdays)
    ]
    return date_list


def scan_table(name="CIBuilds"):
    """ Scans a table returning all results
    """
    items = []
    dynamodb = aws.DB()
    table = dynamodb.table(name)

    # Required because only 1MB are returned
    # See: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.04.html
    response = table.scan()
    for item in response["Items"]:
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


def generate_data(tester):
    """ Generates a validation report

    tester: tester function
    """
    results = scan_table()
    db = OrderedDict()
    metadata = OrderedDict()

    for obj in results:
        obj = box.Box(obj)
        if not tester(obj.job_name):
            continue
        click.echo(f"Processing {obj.job_name}")
        if obj.job_name not in db:
            db[obj.job_name] = {}

        if "build_endtime" not in obj:
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
                obj["build_endtime"], "%Y-%m-%dT%H:%M:%S.%f"
            ).strftime("%Y-%m-%d")
        except:
            day = datetime.strptime(
                obj["build_endtime"], "%Y-%m-%d %H:%M:%S.%f"
            ).strftime("%Y-%m-%d")

        if day not in db[obj.job_name]:
            db[obj.job_name][day] = []
        db[obj.job_name][day].append(obj)
    return db


def generate_validation_report(plan):
    """ Generate validation report
    """

    def tester(line):
        matrix = plan['validation-report']['matrix']
        supported_versions = [
            version
            for mapping in matrix
            for version, _ in mapping.items()
        ]
        jobs = [
            f"validate-{version}-canonical-kubernetes"
            for version in supported_versions
            for job in plan['validation-report']['jobs']
        ]
        return any(line == job for job in jobs)

    days = generate_days()
    metadata = generate_data(tester)
    rows = []
    for jobname, jobdays in sorted(metadata.items()):
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

    return {
        "rows": rows,
        "headers": [
            datetime.strptime(day, "%Y-%m-%d").strftime("%m-%d")
            for day in generate_days()
        ],
        "modified": datetime.now(),
    }


def gen_pages(
    contexts, template_path, out_path, remote_path="s3://jenkaas", static=None
):
    os.makedirs(out_path, exist_ok=True)
    site = Site.make_site(
        contexts=contexts, searchpath=template_path, outpath=out_path
    )
    site.render()
    upload = aws.S3()
    upload.sync_remote(out_path, remote_path)
