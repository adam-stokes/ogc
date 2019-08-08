# Plugin specification

## Built-in Methods

### *get_plugin_option(key)*

Queries options defined in the calling plugin

### *get_spec_option(key)*

Queries options defined in the entire spec (any loaded plugins)

### *doc_plugin_opts(cls)*

**classmethod** Returns markdown rendered table of the calling plugins available options

### *doc_render(cls)*

**classmethod** Renders markdown rendered output of plugin_opts, plugin friendly
  name, description, and an example spec for the plugin.

### *check*

Runs a preliminary check making sure options specified in a spec file exist in the plugin.

### *dep_check*

Parse and print out install commands for plugin dependencies such as apt, snap, and pip.

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
> ogc --spec my-run-spec.yml list-deps
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
> ogc --spec my-run-spec.yml list-deps --installable
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
> ogc --spec my-run-spec.yml list-deps --installable | sh -
```

### *env*

Will read and set host environment variables, along with any DotEnv specified
one or if a properties_file is found (Which uses the Env plugin itself for
that.) Environment variables are merge left, updating any existing key:val
pairs found.

## Not implemented methods

These methods should be defined in the plugin itself as these are not implemented at the spec level.

### *doc_example(cls)*

**classmethod** Optionally return markdown supported output that shows a useful example of how
to use the plugin in a spec file.

### *conflicts*

Useful if there are certain plugin options that can not be run together. Should be overridden in the plugin.

### *process*

Process the plugin, this handles the majority of the plugin's execution task. Should be overridden in the plugin.
