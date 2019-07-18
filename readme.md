# ogc

ogc - Task runner with a focus on deployment/testing/reporting.

# description

OGC is powered by plugins that can be discovered on https://pypi.org with the
prefix of `ogc-plugins`. With plugins installed different aspects of a run can
be defined through a spec file, which is a toml configuration setting up plugin
configuration for the particular goal.

# usage

```
> pip install ogc
> ogc --spec ogc-spec-runner.toml execute

# Or with a ogc.toml file in same directory running ogc from
> ogc execute
```

## Show plugin dependencies

OGC doesn't install package dependencies automatically, but will give you a summary that you can pass to whatever automation strategy you want.

```
> ogc --spec ogc-spec-runner.toml plugin-deps
Plugin dependency summary ::

  - snap:juju/latest/stable
  - snap:juju-wait/latest/stable
  - pip:pytest==5.0.1
```

To get the install commands for the plugin deps you can pass `--installable`:

```
> ogc --spec ogc-spec-runner.toml plugin-deps --installable
snap install juju --channel=latest/stable
snap install juju-wait --channel=latest/stable
pip install pytest==5.0.1
```

Or to handle installing those packages automatically (like in a CI run):

```
> ogc --spec ogc-spec-runner.toml plugin-deps --installable | sh -
```

# todo

Docs..duh.
