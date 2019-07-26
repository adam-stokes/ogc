# OGC Env Plugin
## Description
Environment variable discovery

## Options

| Option | Required | Description |
|:---    |  :---:   |:---|
| name | True | Name of runner |
| description | True | Description of what this runner does |
| long_description | False | An extended description of what this runner does, supports Markdown. |
| tags | False | Global tags to reference during a ogc spec run |
| deps | False | A list of package dependencies needed to run a plugin. |
| env_requires | False | A list of environment variables that must be present for the spec to function. |
| add_to_env | False | Convert certain spec options to an environment variable, these variables will be set in the host environment in the form of **VAR=VAL**. Note: this will convert the dot '.' notation to underscores |
| requires | False | Environment variables that need to exist before the spec can be run |
| properties_file | False | A path to a DotEnv or the like for loading environment variables |


## Example

```toml
[Env]
requires = ["CHARMCREDS", "JUJUCREDS"]

properties_file = "/home/user/env.properties"
```
