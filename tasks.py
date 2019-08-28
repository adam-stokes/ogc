import os

from dotenv import load_dotenv
from invoke import task

load_dotenv()


@task
def clean(c):
    print("Cleaning project")
    c.run("rm -rf site build dist ogc.egg-info __pycache__")


@task
def fix(c):
    c.run("isort -rc -m 3 .")
    c.run("black .")


@task
def test(c):
    c.run("pylint ogc tests")
    c.run("pytest")


@task
def bump_rev(c):
    c.run("punch --part patch")


@task
def dist(c):
    c.run("python3 setup.py bdist_wheel")


@task(pre=[clean, dist])
def install(c):
    c.run("pip install --upgrade dist/*whl --force")


@task(pre=[clean, fix, test, bump_rev, dist])
def upload(c):
    c.run("twine upload dist/*")


@task
def upload_docs(c):
    WEB_USER = os.getenv("WEB_USER")
    WEB_SITE = os.getenv("WEB_SITE")
    WEB_DST = os.getenv("WEB_DST")

    c.run("pip install -rrequirements_doc.txt")
    c.run("cp readme.md docs/index.md")
    c.run("mkdocs build")
    c.run(f"rsync -avz --delete site/* {WEB_USER}@{WEB_SITE}:{WEB_DST}")
