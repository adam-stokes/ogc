from dotenv import load_dotenv
from invoke import task
from pathlib import Path
import os

load_dotenv()


@task
def clean(c):
    print("Cleaning project")
    c.run("rm -rf site build dist ogc.egg-info __pycache__ artifacts")


@task
def fix(c):
    c.run("isort -m 3 ogc")
    # c.run("black .")


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


@task
def prep(c):
    c.run("click-man ogc -t man")
    for fname in Path("man").glob("*.1"):
        dst = Path("docs/commands") / f"{fname.stem}.md"
        c.run(f"pandoc -f man -t markdown {fname} -o {dst}")


@task(pre=[clean, fix, prep, bump_rev])
def release(c):
    pypi_user = os.environ.get("PYPI_USER")
    pypi_pass = os.environ.get("PYPI_PASS")
    c.run("mkdocs gh-deploy")
    c.run(f"poetry publish --build -u {pypi_user} -p {pypi_pass}")
    c.run("git commit -asm 'Next Release'")
    c.run("git push --tags")
