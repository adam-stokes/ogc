[![Build Status](https://travis-ci.org/battlemidget/ogc.svg?branch=master)](https://travis-ci.org/battlemidget/ogc)

# OGC, a runner of things

ogc - Task runner with a focus on deployment/testing/reporting.

## Description

OGC is powered by plugins that can be discovered on https://pypi.org with the
prefix of `ogc-plugins`. With plugins installed different aspects of a run can
be defined through a spec file, which is a yaml file setting up plugin
configuration for the particular goal.

## Usage

```
> pip install ogc
> ogc --spec ogc-spec-runner.yml execute

# Or with a ogc.yml file in same directory running ogc from
> ogc execute
```

## Add plugins

To make *OGC* a bit more useful, install a few plugins:

```
> pip install ogc-plugins-runner
```

This will allow you to add functionality such as running scripts and preparing
environment variables. Please see the plugins section of the docs for more
information.

```yaml

meta:
  name: A test spec
  description: A simple spec showing how to run commands

plan:
  - runner:    # This is the plugin from ogc-plugins-runner
      description: Clean out build directory
      cmd: rm -rf build
      tags: [clean]
```

## More information

- [Website / Documentation](https://ogc.8op.org)
