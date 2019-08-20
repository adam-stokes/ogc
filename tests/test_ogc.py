from pathlib import Path

import pytest

from ogc.enums import SPEC_CORE_PLUGINS, SpecPhase
from ogc.spec import SpecConfigException, SpecLoader, SpecPlugin
from ogc.state import app

fixtures_dir = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def runners():
    """ Fixture with the parsed runners
    """
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    return [runner for runner in spec["plan"]]


def test_load_spec_phases():
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    phases = [phase for phase in spec.keys() if phase not in SPEC_CORE_PLUGINS]
    assert phases not in SPEC_CORE_PLUGINS
    assert phases == [SpecPhase.SETUP, SpecPhase.PLAN]


def test_nested_assets(mocker):
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    plug = SpecPlugin(SpecPhase.PLAN, spec[SpecPhase.PLAN][3]["runner"], spec)
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
    spec = SpecPlugin(SpecPhase.PLAN, spec[SpecPhase.PLAN][0]["runner"], spec)
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
    plug = SpecPlugin(SpecPhase.SETUP, spec[SpecPhase.SETUP][0]["juju"], spec)

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
    plug = SpecPlugin(SpecPhase.SETUP, spec[SpecPhase.SETUP][0]["juju"], spec)

    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    assert plug.opt("deploy.reuse") is True


# pylint: disable=redefined-outer-name
def test_env_requires(runners, mocker):
    """ Make sure env-requires works as expected
    """
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / "spec.yml"])
    for task in runners:
        if "env-requires" in task["runner"]:
            spec = SpecPlugin("plan", task["runner"], spec)
            with pytest.raises(SpecConfigException):
                spec.check()

            app.env["RUNNER_OPT"] = "YES"
            with pytest.raises(SpecConfigException) as exc_info:
                spec.check()
            assert str(exc_info.value) == (
                "ANOTHER_OPT, TEST_ENV are missing from the "
                "required environment variables, please make "
                "sure those are loaded prior to running."
            )
