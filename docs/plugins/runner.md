# OGC Runner Plugin
## Description
<class 'ogc_plugins_runner.Runner'>

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
| description | True | Description of the running task |
| concurrent | False | Allow this runner to run concurrenty in the background |
| cmd | False | A command to run |
| script | False | A blob of text to execute, usually starts with a shebang interpreter |
| timeout | False | Do not exceed this timeout in seconds |
| wait-for-success | False | Wait for this runner to be successfull, will retry. Useful if you are doing a status check on a service that will eventually become ready. |
| fail-silently | False | Do not halt on a failed runner, this will print an errorthat can be logged for ci runs, but still allow all runners in a spec to complete. |
| back-off | False | Time in seconds to wait between retries |
| retries | False | Max number of retries |
| assets | False | Assets configuration |
| assets.name | False | Name of asset |
| assets.source-file | False | A file to act on, (ie. a configuration file) |
| assets.source-blob | False | A text blob of a file to use |
| assets.destination | False | Where to output this asset, (ie. saving a pytest.ini blob to a tests directory) |
| assets.is-executable | False | Make this asset executable |


## Example

Variations of using entry points, script blob, and script files, with and without assets.

```toml
[[Runner]]
name = "Sync K8s snaps"
description = """
Pull down upstream release tags and make sure our launchpad git repo has those
tags synced. Next, we push any new releases (major, minor, or patch) to the
launchpad builders for building the snaps from source and uploading to the snap
store.
"""
deps = ["pip:requirements.txt"]
env_requires = ["SNAP_LIST"]
entry_point = ["python3", "-m", "snap.py"]
args = ["sync-upstream", "--snap-list", "$SNAP_LIST"]
tags = ["sync"]

[[Runner]]
name = 'Run pytest'
description = 'a description'
run_script = 'scripts/test-flaky'
deps = ['pip:pytest', 'pip:flaky>=3.0.0']

[[Runner.assets]]
name = 'pytest config'
source_file = 'data/pytest.ini'
destination = 'jobs/pytest.ini'
is_executable = false

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

juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER
"""
timeout = 180
tags = ["teardown"]
```
