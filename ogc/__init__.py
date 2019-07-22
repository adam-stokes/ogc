"""
---
title: OGC, a runner of things
targets: ['readme.md', 'docs/index.md']
---

[![Build Status](https://travis-ci.org/battlemidget/ogc.svg?branch=master)](https://travis-ci.org/battlemidget/ogc)

# {title}

ogc - Task runner with a focus on deployment/testing/reporting.

## Description

OGC is powered by plugins that can be discovered on https://pypi.org with the
prefix of `ogc-plugins`. With plugins installed different aspects of a run can
be defined through a spec file, which is a toml file setting up plugin
configuration for the particular goal.

## Usage

```
> pip install ogc
> ogc --spec ogc-spec-runner.toml execute

# Or with a ogc.toml file in same directory running ogc from
> ogc execute
```

## Add plugins

To make *OGC* a bit more useful, install a few plugins:

```
> pip install ogc-plugins-runner
> pip install ogc-plugins-env
```

This will allow you to add functionality such as running scripts and preparing
environment variables. Please see the plugins section of the docs for more
information.

### Show plugin dependencies

OGC doesn't install plugin dependencies automatically, but will give you a
summary that you can pass to whatever automation strategy you want.

```
> ogc --spec ogc-spec-runner.toml plugin-deps
```

Output:

```
Plugin dependency summary ::

  - apt:python3-markdown
  - snap:juju/latest/stable:classic
  - snap:juju-wait/latest/stable:classic
  - pip:pytest==5.0.1
```

To get the install commands for the plugin deps you can pass `--installable`:

```
> ogc --spec ogc-spec-runner.toml plugin-deps --installable
```

Output:

```
sudo apt install -qyf python3-markdown
sudo snap install juju --channel=latest/stable --classic
sudo snap install juju-wait --channel=latest/stable --classic
pip install --user pytest==5.0.1
```

Or to handle installing those packages automatically (like in a CI run):

```
> ogc --spec ogc-spec-runner.toml plugin-deps --installable | sh -
```
"""
