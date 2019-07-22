# OGC Charm Plugin
## Description
Charm plugin for building Juju charms and bundles

## Options

| Option | Required | Description |
|:---    |  :---:   |:---|
| tags | False | Global tags to reference during a ogc spec run |
| deps | False | A list of package dependencies needed to run a plugin. |
| add_to_env | False | Convert certain spec options to an environment variable, these variables will be set in the host environment in the form of **VAR=VAL**. Note: this will convert the dot '.' notation to underscores |
| charms.charm_branch | True | GIT branch of the charm to build from |
| charms.to_channel | True | Charmstore channel to publish built charm to |
| charms.filter_by_tag | False | Build tag to filter by, (ie. k8s or general) |
| charms.list | True | Path to a yaml list of charms to build |
| charms.resource_spec | False | Path to yaml list resource specifications when building charm resources |
| charms.layer_index | False | Path to public layer index |
| charms.layer_list | False | Path to yaml list of layers to cache prior to a charm build |
| charms.layer_branch | False | GIT Branch to build layers from |
| bundles.list | False | Path to yaml list of bundles to build |
| bundles.repo | False | GIT Bundle repo |
| bundles.filter_by_tag | False | Build tag to filter by, (ie. k8s or general) |


## Example

```toml
[Charm]
name = "Building Charms"
description = """
Build the charms that make up a Juju bundle
"""

[Charm.charms]
charm_branch = "master"
filter_by_tag = "k8s"
layer_branch = "master"
layer_index = "https://charmed-kubernetes.github.io/layer-index/"
layer_list = "builders/charms/charm-layer-list.yaml"
list = "builders/charms/charm-support-matrix.yaml"
resource_spec = "builders/charms/resource-spec.yaml"
to_channel = "edge"

[Charm.bundles]
filter_by_tag = "k8s"
bundle_list = "builders/charms/charm-bundles-list.yaml"
deps = ["snap:charm/latest/edge:classic"]
```
