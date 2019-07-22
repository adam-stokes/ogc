# Plugin specification

## Built-in Methods

**def:check** - Runs a preliminary check making sure options specified in a spec file exist in the plugin.

**def:dep_check** - Parse and print out install commands for plugin dependencies such as apt, snap, and pip.

This allows each plugin to define dependencies required to run. Take note that
this won't actually install the plugin deps for you, however, it does make it easy to
install those deps for all loaded plugins:

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

**def:env** - Will read and set host environment variables, along with any DotEnv
  specified one or if a properties_file is found (Which uses the Env plugin
  itself for that.) Environment variables are merge left, updating any existing
  key:val pairs found.

## Not implemented methods

These methods must be defined in the plugin itself as these are not implemented at the spec level.

**def:conflicts** - Useful if there are certain plugin options that can not be run together. Should be overridden in the plugin.

**def:process** - Process the plugin, this handles the majority of the plugin's execution task. Should be overridden in the plugin.