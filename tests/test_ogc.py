import yaml
import os
from pathlib import Path
from ogc.spec import SpecLoader, SpecPlugin
from ogc.state import app
from ogc.enums import SpecPhase, SPEC_PHASES, SPEC_CORE_PLUGINS

fixtures_dir = Path(__file__).parent / 'fixtures'


def test_load_spec_phases():
    spec = SpecLoader.load([fixtures_dir / 'spec.yml'])
    phases = [
        phase for phase in spec.keys()
        if phase not in SPEC_CORE_PLUGINS
    ]
    assert phases not in SPEC_CORE_PLUGINS
    assert phases == [SpecPhase.SETUP, SpecPhase.PLAN]

def test_nested_assets(mocker):
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / 'spec.yml'])
    plug = SpecPlugin(SpecPhase.PLAN, spec[SpecPhase.PLAN][3]["runner"], spec)
    assets = plug.opt("assets")
    assert assets[0]["name"] == "pytest configuration"


def test_cmd_to_env(mocker):
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / 'spec.yml'])
    plug = SpecPlugin(SpecPhase.PLAN, spec[SpecPhase.PLAN][0]["runner"], spec)
    _env = {}
    _env["BONZAI"] = "bonzai-test"
    _env["ANOTHERTIME"] = "this happened late"
    _env["VAR_NICE"] = "interesting concept"
    _env["CONTROLLER"] = "juju-controller"
    _env["MODEL"] = "juju-model"
    app.env = _env
    spec = SpecPlugin(SpecPhase.PLAN, spec[SpecPhase.PLAN][0]["runner"], spec)
    cmd = spec.opt("cmd")
    assert cmd == ("echo bonzai-test lthis happened "
                   "late envinteresting concept "
                   "juju-controller:juju-model "
                   "juju-controller juju-model")


def test_get_option_env_key(mocker):
    """ Tests that an environment variable set for a given option is converted
    into the hosts environment setting """
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / 'spec.yml'])
    plug = SpecPlugin(SpecPhase.SETUP, spec[SpecPhase.SETUP][0]["juju"], spec)

    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    assert plug.opt("deploy.cloud") == "aws/us-east-1"
    assert plug.opt("deploy.controller") == "test-controller"
    assert plug.opt("deploy.model") == "test-model"


def test_get_option_env_key_bool(mocker):
    """ Tests that get_plugin_option handles boolean values correctly
    """
    mocker.patch("ogc.state.app.log")
    spec = SpecLoader.load([fixtures_dir / 'spec.yml'])
    plug = SpecPlugin(SpecPhase.SETUP, spec[SpecPhase.SETUP][0]["juju"], spec)

    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    assert plug.opt("deploy.reuse") is True
