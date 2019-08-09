# OGC Env Plugin
## Description
<class 'ogc_plugins_env.Env'>

## Options

| Option | Required | Description |
|:---    |  :---:   |:---|
| name | False | Name of runner |
| description | False | Description of what this runner does |
| long-description | False | An extended description of what this runner does, supports Markdown. |
| tags | False | Global tags to reference during a ogc spec run |
| deps | False | A list of package dependencies needed to run a plugin. |
| env-requires | False | A list of environment variables that must be present for the spec to function. |
| add-to-env | False | Convert certain spec options to an environment variable, these variables will be set in the host environment in the form of **VAR=VAL**. Note: this will convert the dot '.' notation to underscores |
| requires | False | Environment variables that need to exist before the spec can be run |
| properties-file | False | A path to a DotEnv or the like for loading environment variables |

