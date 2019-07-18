# ogc

ogc - Task runner with a focus on deployment/testing/reporting.

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
> ogc --spec ogc-spec-runner.toml plugin-deps --installable --with-sudo
```

# description

OGC is powered by plugins that can be discovered on https://pypi.org with the
prefix of `ogc-plugins`. With plugins installed different aspects of a run can
be defined through a spec file, which is a toml configuration setting up plugin
configuration for the particular goal.

# todo

Docs..duh.
