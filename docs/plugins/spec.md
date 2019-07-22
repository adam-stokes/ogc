# Plugin specification

## Methods

This allows each plugin to define dependencies required to run. Take note that
this won't actually install the plugin deps for you, however, it does make it easy to
install those deps for all loaded plugins:

**check** - Runs a preliminary making sure options specified in a spec file exist in the plugin.

**dep_check** - Parse and print out install commands for plugin dependencies such as apt, snap, and pip.

Current Supported formats:

| Type | Args | Description | Example |
| :--- | :--: | :---        | :---    |
| apt  | PKG_NAME |  Will access apt-get package manager for installation | apt:python3-test
| pip  | PKG_NAME>=PIP_VERSION | pip format | pip:black>=0.10.0,<1.0.0 |
| snap | PKG_NAME/track/channel | snap format, track can be a version like 1.15, channel is stable, candidate, beta, edge.| snap:kubectl/1.15/edge:classic |

A plugin dependency can be in the following form:

```toml
[[Runner]]
deps = ['apt:python3-pytest', 'pip:pytest-asyncio==5.0.1', 'snap:kubectl/1.15/edge:classic']
```

A user can then get that information prior to running so that all requirements are met.

```
> ogc --spec my-run-spec.toml plugin-deps
```

**Returns**:

```
Required Dependencies:
  - apt:python3-pytest
  - apt:wget
  - pip:pytest-asyncio==5.0.1
  - snap:kubectl/1.15/edge
```

To show the dependencies in a way that can be easily installed for automated runs:

```
> ogc --spec my-run-spec.toml plugin-deps --installable
```

**Returns**:

```
sudo apt-get install -qyf python3-pytest
sudo apt-get install -qyf wget
pip install --user pytest-asyncio==5.0.1
snap install kubectl --channel=1.15/edge
```

You can install them automatically with:
```
> ogc --spec my-run-spec.toml plugin-deps --installable --with-sudo | sh -
```