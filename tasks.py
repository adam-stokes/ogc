from dotenv import load_dotenv
from invoke import task

load_dotenv()


@task
def clean(c):
    print("Cleaning project")
    c.run("rm -rf site build dist ogc.egg-info __pycache__")


@task
def fix(c):
    c.run("isort -m 3 ogc")
    c.run("black .")


@task
def test(c):
    c.run("pylint ogc tests")
    c.run("pytest")


@task
def bump_rev(c):
    c.run("punch --part patch")


@task
def celery(c):
    c.run("ogc server")
