import toml
import os
from ogc.spec import SpecPlugin
from ogc.state import app


def test_load_spec():
    spec_toml = toml.loads(
        """
[Info]
name = 'A test spec'
"""
    )
    spec = SpecPlugin(spec_toml["Info"], spec_toml)
    assert "name" in spec.spec


def test_nested_args_to_env(mocker):
    mocker.patch("ogc.state.app.log")
    spec_toml = toml.loads(
        """
[[Runner.assets]]
name = 'pytest config'
description = 'pytest asset test'
source_file = 'data/pytest.ini'
destination = 'jobs/pytest.ini'
is_executable = false

[[Runner.assets]]
name = 'boom config'
description = 'pytest asset test'
source_file = 'data/pytest.ini'
destination = 'jobs/pytest.ini'
is_executable = false

"""
    )
    spec = SpecPlugin(spec_toml["Runner"], spec_toml)
    assets = spec.get_plugin_option("assets")
    assert assets[0]['name'] == 'pytest config'


def test_args_to_env(mocker):
    mocker.patch("ogc.state.app.log")

    spec_toml = toml.loads(
        """
[Runner]
name = 'A test runner with args'
args = ["run",
        "$BONZAI",
        "l$ANOTHERTIME",
        "env$VAR_NICE",
        "$CONTROLLER:$MODEL",
        "$CONTROLLER $MODEL"]
"""
    )
    _env = {}
    _env["BONZAI"] = "bonzai-test"
    _env["ANOTHERTIME"] = "this happened late"
    _env["VAR_NICE"] = "interesting concept"
    _env["CONTROLLER"] = "juju-controller"
    _env["MODEL"] = "juju-model"
    app.env = _env
    spec = SpecPlugin(spec_toml["Runner"], spec_toml)
    items = spec.get_plugin_option("args")
    assert items == [
        "run",
        "bonzai-test",
        "lthis happened late",
        "envinteresting concept",
        "juju-controller:juju-model",
        "juju-controller juju-model",
    ]


def test_get_option_env_key(mocker):
    """ Tests that an environment variable set for a given option is converted into the hosts environment setting
    """
    mocker.patch("ogc.state.app.log")
    spec_toml = toml.loads(
        """
[Juju]
cloud = "$JUJU_CLOUD"
model_controller = "$JUJU_CONTROLLER:$JUJU_MODEL"
"""
    )
    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    spec = SpecPlugin(spec_toml["Juju"], spec_toml)
    assert spec.get_plugin_option("cloud") == "aws/us-east-1"
    assert spec.get_plugin_option("model_controller") == "test-controller:test-model"


def test_get_option_env_key_bool(mocker):
    """ Tests that get_plugin_option handles boolean values correctly
    """
    mocker.patch("ogc.state.app.log")
    spec_toml = toml.loads(
        """
[Juju]
reuse = true
cloud = "$JUJU_CLOUD"
model_controller = "$JUJU_CONTROLLER:$JUJU_MODEL"
"""
    )
    _env = {}
    _env["JUJU_CLOUD"] = "aws/us-east-1"
    _env["JUJU_CONTROLLER"] = "test-controller"
    _env["JUJU_MODEL"] = "test-model"
    app.env = _env
    spec = SpecPlugin(spec_toml["Juju"], spec_toml)
    assert spec.get_plugin_option("reuse") is True
