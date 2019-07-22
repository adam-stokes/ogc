#OGC Env Plugin
## Description
Environment variable discovery

## Options

| Option | Required | Description |
|:---    |  :---:   |:---|
| tags | False | Global tags to reference during a ogc spec run |
| deps | False | A list of package dependencies needed to run a plugin. |
| add_to_env | False | Convert certain spec options to an environment variable, these variables will be set in the host environment in the form of **VAR=VAL**. Note: this will convert the dot '.' notation to underscores |
| requires | False | Environment variables that need to exist before the spec can be run |
| properties_file | False | A path to a DotEnv or the like for loading environment variables |


## Example

```toml
[Env]
# OGC Env looks for environment variables in the following order
# 1. Parses current host ENV
# 2. Checks for a .env in the cwd, merging left and overwriting vars from #1
# 3. Checks for `properties_file`, merging left overwriting vars from #1 and #2
# Test plans require certain environment variables to be set prior to running.
# This module allows us to make sure those requirements are met before
# proceeding.
requires = ["CHARMCREDS", "JUJUCREDS"]

# Optionally, define a location of KEY=VALUE line items to use as this specs
# environment variables. This will meld into host environment updating any variables overlapping
properties_file = "/home/user/env.properties"

# Convert certain spec options to ane environment variable, these variables
# will be set in the host environment in the form of VAR=VAL. Note: this
# will convert the dot '.' notation to underscores
add_to_env = ['Juju.cloud', 'Juju.controller']
```
