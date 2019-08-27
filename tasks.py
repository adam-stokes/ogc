from invoke import task


@task
def clean(c):
    c.run("rm -rf build dist ogc.egg-info __pycache__")


@task
def fix(c):
    c.run("isort -rc -m 3 .")
    c.run("black .")
    c.run("pylint ogc")


@task
def test(c):
    c.run("pytest")


@task
def bump_rev(c):
    c.run("punch --part patch")


@task
def dist(c):
    c.run("python3 setup.py bdist_wheel")


@task
def install(c):
    c.run("pip install --upgrade dist/*whl --force")


@task
def upload(c):
    c.run("twine upload dist/*")


@task
def docs(c):
    c.run("python3 tools/docgen")
