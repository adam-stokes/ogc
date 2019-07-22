# Plugin Specification

This allows each plugin to define dependencies required to run. Take note that
this won't actually install the plugin deps for you, however, it does make it easy to
install those deps for all loaded plugins:

## Usage

Functions supported.

## Defining plugin dependencies

```
[[Runner]]
name = 'Running a python script'
executable = 'python3'
run_script = 'bin/script.py'
deps = ['apt:python3-pytest', 'pip:pytest-asyncio==5.0.1', 'snap:kubectl/1.15/edge']

[[Runner]]
name = 'Running a script'
run = '''
#!/bin/bash
wget http://example.com/zip
'''
deps = ['apt:wget']
```

To show the required dependencies run:
```
> ogc --spec my-run-spec.toml plugin-deps

Required Dependencies:
  - apt:python3-pytest
  - apt:wget
  - pip:pytest-asyncio==5.0.1
  - snap:kubectl/1.15/edge
```

To show the dependencies in a way that can be easily installed for automated runs:
```
> ogc --spec my-run-spec.toml plugin-deps --installable
sudo apt-get install -qyf python3-pytest
sudo apt-get install -qyf wget
pip install --user pytest-asyncio==5.0.1
snap install kubectl --channel=1.15/edge
```

You can optionally pass sudo with it:
```
> ogc --spec my-run-spec.toml plugin-deps --installable
sudo apt-get install -qyf python3-pytest
sudo apt-get install -qyf wget
pip install --user pytest-asyncio==5.0.1
sudo snap install kubectl --channel=1.15/edge
```
You can install them automatically with:
```
> ogc --spec my-run-spec.toml plugin-deps --installable --with-sudo | sh -
Supported formats:
apt: <package name> Will access apt-get package manager for installation
pip: <packagename>==<optional version> pip format
snap: <packagename>/track/channel, snap format, track can be a version like 1.15, channel is stable, candidate, beta, edge.
```