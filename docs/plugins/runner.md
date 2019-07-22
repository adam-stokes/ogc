#OGC Runner Plugin
## Description
Allow running of shell scripts, and other scripts where the runner has access to the executable

## Options

| Option | Required | Description |
|:---    |  :---:   |:---|
| tags | False | Global tags to reference during a ogc spec run |
| deps | False | A list of package dependencies needed to run a plugin. |
| add_to_env | False | Convert certain spec options to an environment variable, these variables will be set in the host environment in the form of **VAR=VAL**. Note: this will convert the dot '.' notation to underscores |
| name | True | Name of runner |
| description | True | Description of what this runner does |
| concurrent | False | Allow this runner to run concurrenty in the background |
| run | False | A blob of text to execute, usually starts with a shebang interpreter |
| run_script | False | Path to a excutable script |
| executable | False | Must be set when using `run_script`, this is the binary to run the script with, (ie. python3) |
| timeout | False | Do not exceed this timeout in seconds |
| wait_for_success | False | Wait for this runner to be successfull, will retry. Useful if you are doing a status check on a service that will eventually become ready. |
| back_off | False | Time in seconds to wait between retries |
| retries | False | Max number of retries |
| assets | False | Assets configuration |
| assets.name | False | Name of asset |
| assets.source_file | False | A file to act on, (ie. a configuration file) |
| assets.source_blob | False | A text blob of a file to use |
| assets.destination | False | Where to output this asset, (ie. saving a pytest.ini blob to a tests directory) |
| assets.is_executable | False | Make this asset executable |


## Example

This shows 4 runners that execute sequentially.

```toml
[[Runner]]
name = "Running CNCF Conformance"
description = """
See https://www.cncf.io/certification/software-conformance/ for more information.
"""
run = """
#!/bin/bash
set -eux

mkdir -p $HOME/.kube
juju scp -m $JUJU_CONTROLLER:$JUJU_MODEL kubernetes-master/0:config $HOME/.kube/
export RBAC_ENABLED=$(kubectl api-versions | grep "rbac.authorization.k8s.io/v1beta1" -c)
kubectl version
sonobuoy version
sonobuoy run
"""

tags = ["cncf", "cncf-run"]

[[Runner]]
name = "Waiting for Sonobuoy to complete"
description = """
See https://www.cncf.io/certification/software-conformance/ for more information.
"""
run = """
#!/bin/bash
set -eux

sonobuoy status|grep -q 'Sonobuoy has completed'
"""
wait_for_success = true
timeout = 10800
back_off = 15
tags = ["cncf", "cncf-wait-status"]

[[Runner]]
name = "Downloading conformance results"
description = "Download results"
run = """
#!/bin/bash
set -eux

sonobuoy retrieve results/.
kubectl version
"""
wait_for_success = true
back_off = 5
retries = 5
tags = ["cncf", "cncf-download-results"]

[[Runner]]
name = "Tearing down deployment"
description = "Tear down juju"
run = """
#!/bin/bash
set -eux

juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER"
"""
timeout = 180
tags = ["teardown"]
```
