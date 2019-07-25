# OGC Juju Plugin
## Description
Juju plugin for bootstrap and deployment of applications

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
| cloud | True | Name of one of the support Juju clouds to use. |
| controller | True | Name of the controller to create with Juju. |
| model | True | Name of the model to create with Juju. |
| bootstrap | False | Juju bootstrap options. |
| bootstrap.constraints | False | Juju bootstrap constraints |
| bootstrap.debug | False | Turn on debugging during a bootstrap |
| bootstrap.disable_add_model | False | Do not immediately add a Juju model after bootstrap. Useful if juju model configuration needs to be performed. |
| deploy | False | Juju deploy options |
| deploy.reuse | False | Reuse an existing Juju model, please note that if applications exist and you deploy the same application it will create additional machines. |
| deploy.bundle | True | The Juju bundle to use |
| deploy.overlay | False | Juju bundle fragments that can be overlayed a base bundle. |
| deploy.bundle_channel | True | Juju bundle channel to deploy from. |
| deploy.charm_channel | True | Juju charm channel to deploy from. Typically, same as the bundle channel unless you are deploying individual charms. |
| deploy.wait | False | Juju deploy is asynchronous. Turn this option on to wait for a deployment to settle. |
| config | False | Juju charm config options |
| config.set | False | Set a Juju charm config option |


## Example

```toml
[Juju]
# Juju module for bootstrapping and deploying a bundle
cloud = "aws"

# controller to create
controller = "validator"

# model to create
model = "validator-model"

[Juju.bootstrap]
# turn on debugging
debug = false

# disable adding the specified model, usually when some configuration on the
# models have to be done
disable-add-model = true

[Juju.deploy]
# reuse existing controller/model
reuse = True

# bundle to deploy
# bundle = "cs:~owner/custom-bundle"
bundle = "bundles/my-custom-bundle.yaml"

# Optional overlay to pass into juju
overlay = "overlays/1.15-edge.yaml"

# Optional bundle channel to deploy from
bundle_channel = "edge"

# Optional charm channel to deploy from
charm_channel = "edge"

# Wait for a deployment to settle?
wait = true

[Juju.config]
# Config options to pass to a deployed application
# ie, juju config -m controller:model kubernetes-master allow-privileged=true
set = ["kubernetes-master = allow-privileged=true",
       "kubernetes-worker = allow-privileged=true"]
```
