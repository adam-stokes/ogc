from pathlib import Path

import pytest

from ogc import run
from ogc.enums import SpecCore
from ogc.spec import SpecLoader, SpecPlugin
from ogc.exceptions import SpecProcessException
from ogc.state import app

fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def runners():
    """ Fixture with the parsed runners
    """
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    return [runner for runner in spec["plan"]["script"]]


def test_nested_assets(mocker):
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    plug = SpecPlugin(spec[SpecCore.PLAN]["script"][3]["runner"])
    assets = plug.opt("assets")
    assert assets[0]["name"] == "pytest configuration"


def test_cmd_to_env(mocker):
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    _env = {}
    _env["BONZAI"] = "bonzai-test"
    _env["ANOTHERTIME"] = "this happened late"
    _env["VAR_NICE"] = "interesting concept"
    _env["CONTROLLER"] = "juju-controller"
    _env["MODEL"] = "juju-model"
    app.env = _env
    spec = SpecPlugin(spec[SpecCore.PLAN]["script"][0]["runner"])
    cmd = spec.opt("cmd")
    assert cmd == (
        "echo bonzai-test lthis happened "
        "late envinteresting concept "
        "juju-controller:juju-model "
        "juju-controller juju-model"
    )


def test_get_option_env_key(mocker):
    """ Tests that an environment variable set for a given option is converted
    into the hosts environment setting """
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    plug = SpecPlugin(spec[SpecCore.PLAN]["before-script"][0]["juju"])

    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    assert plug.opt("cloud") == "aws/us-east-1"
    assert plug.opt("controller") == "test-controller"
    assert plug.opt("model") == "test-model"


def test_get_option_env_key_bool(mocker):
    """ Tests that get_plugin_option handles boolean values correctly
    """
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    plug = SpecPlugin(spec[SpecCore.PLAN]["before-script"][0]["juju"])

    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    assert plug.opt("deploy.reuse") is True


def test_run_script_passes_check(mocker):
    """ Tests that we can run shell commands
    """
    mocker.patch("ogc.state.app.log")
    run.script("ls -l", env=app.env.copy())


def test_run_script_blob_passes_check(mocker):
    """ Tests that we can run shell scripts
    """
    mocker.patch("ogc.state.app.log")
    blob = """
#!/bin/bash
set -x
ls -l
"""
    run.script(blob, env=app.env.copy())


def test_run_script_fails_check(mocker):
    """ Tests that we can run shell scripts
    """
    mocker.patch("ogc.state.app.log")
    with pytest.raises(SpecProcessException):
        run.script("ls -l\necho HI\nexit 1", env=app.env.copy())
