# OGC Specification

The spec file composed of configuration items in yaml format. There are
currently 2 top level properties that are accessed when the specification is
executed, the first is **meta** and the second is **plan**.

## Spec properties

There are a couple top level properties that can be set that would effect the
operation of the specification plan.

### Example

```yaml
# Run jobs sequentially
sequential: yes
```

### Properties

| Name | Description |
| -    | -           |
| sequential | Run plan jobs sequentially (default: no) |


## Meta specification

The **meta** section provides more information on what the job does along with
certain properties that make generating specification documentation streamlined.

### Example

```yaml
meta:
  mkdocs:
    destination:
      - "releases/bugfix/index.md"
  name: Creating a bugfix release
  description: |
    Performs a Kubernetes bugfix release, which includes validation across the base
    deployment as well as variations including calico, tigera, vault, nvidia, and
    ceph.
  long-description: |
    ## Bugfix Release Process

    ### Cherry-pick fixes from master into stable branches

    ### Document release notes

    - Bugfixes
    - Enhancements
    - Known Limitations/Issues
```
### Properties

| Name | Description |
| -    | -           |
| name | The name of the spec |
| description | A short summary of what the spec is |
| long-description | A longer description of what the spec does, suppors **markdown** syntax. |

As seen in the above example there is a **mkdocs** property defined. This
configuration makes use of one of OGC's plugin called **ogc-plugins-spec-doc**.

When this plugin is executed it will go through and find all specification files
in the current directory and will convert them in a way that **mkdocs** can
generate documentation. This makes it easy to keep both the execution
environment and the documentation of what the specification does in a single
file.

The **destination** defined is where the resulting documentation will be
placed, for instance, this document will be copied over to
**docs/releases/bugfix/index.md** so that **mkdocs** will pick it up during
build.

To use this plugin:

```
pip install ogc-plugins-spec-doc
```

Configuring the plugin itself is done through an OGC Spec file of its own, for
example, we have a file called **maintainer-spec.yml**:

```yaml
meta:
  name: k8s ci maintainer spec
  description: |
    OGC Spec for generating documentation, running unittests, etc.

plan:
  - script:
      - specdoc:
          file-glob: jobs/**/*spec.yml
          top-level-dir: .
      - mkdocs build
```

Running this specifiation will collect all specifications matching the file glob
along with building the documentation through **mkdocs**.


## Plan specification

The **plan** section provides access to options that allow you model what your
execution environment will look like and how it will be run and validated.

### Example

```yaml

plan:
  - &BASE_JOB
    env:
      - SNAP_VERSION=1.17/edge
      - JUJU_DEPLOY_BUNDLE=cs:~containers/charmed-kubernetes
      - JUJU_DEPLOY_CHANNEL=edge
      - JUJU_CLOUD=aws/us-east-1
      - JUJU_CONTROLLER=validate-ck
      - JUJU_MODEL=validate-model
    if: '[[ $(date +"%A") != "Sunday" ]] && [[ $(date +"%A") != "Saturday" ]]'
    before-script:
      - juju kill-controller -y $JUJU_CONTROLLER || true
      - !include jobs/spec-helpers/bootstrap.yml
    script:
      - !include jobs/spec-helpers/pytest.yml
    after-script:
      - !include jobs/spec-helpers/collect.yml
      - juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.16/stable
      - JUJU_DEPLOY_BUNDLE=cs:~containers/charmed-kubernetes
      - JUJU_DEPLOY_CHANNEL=stable
      - JUJU_CLOUD=aws/us-east-1
      - JUJU_CONTROLLER=validate-ck
      - JUJU_MODEL=validate-model
    script:
      - runner:
          timeout: 7200
          script: |
            #!/bin/bash
            set -x

            pytest $INTEGRATION_TEST_PATH/validation.py \
               --cloud $JUJU_CLOUD \
               --model $JUJU_MODEL \
               --controller $JUJU_CONTROLLER 2>&1
```


### Properties

| Name | Description |
| -    | -           |
| env | Environment variables |
| if | A conditional build statement |
| before-script | **before-script** phase |
| script | **script** phase |
| after-script | **after-script** phase |


### Conditional Variants

Defining when a variant should run is done through the **if** conditional and
supports single line bash for handling its tests. For example, on `line 10` the
first variant states that it will run every execution _unless_ the hosts system
clock returns **Sunday** or **Saturday** at which point this variant is then
skipped.

### How it works

Each plan consists of a list of tasks to be run, those tasks define all aspects
of the execution environment from setup to teardown. Each one of these tasks is
known as a **variant** and a variant utilizes YAML functionality for defining
nuances between each variant.

One of the YAML features that is heavily used is anchors, you can see how those
anchors are used in the above example on `lines 2 and 19`. These anchors simply
provide the same variant over and over while allowing different sections to be
manipulated to accomodate any testing requirements.

For example, `line 4` of the above example states we need to have the environment
variable **SNAP_VERSION** set to **1.17/edge**, but on `line 21` we want to test a
different version so we update our environment to include **SNAP_VERSION** as
**1.16/stable**.

!!! Note
    For each section that needs updating in the subsequent tasks must provide
    the entire stanza and not just the specific line changes. So if you need to
    set something in the **env** section for another variant you must make sure
    to include any of the other line items that did not change from variant to
    variant as seen on `lines 4-9` and `lines 21-26`.


#### Variant Includes

Another feature of the plan which is aimed at reducing boilerplate is the
ability to `!include` other yaml files. For example, on `line 13` we want to
include the specifications needed to bootstrap an environment prior to running
any tests. The contents of that file is:

```yaml
juju:
  cloud: $JUJU_CLOUD
  controller: $JUJU_CONTROLLER
  model: $JUJU_MODEL
  bootstrap:
    constraints: "arch=amd64"
    debug: no
    replace-controller: yes
    model-default:
      - test-mode=true
      - resource-tags=owner=k8sci
  deploy:
    reuse: no
    bundle: $JUJU_DEPLOY_BUNDLE
    overlay: |
      applications:
        kubernetes-master:
          options:
            channel: $SNAP_VERSION
        kubernetes-worker:
          options:
            channel: $SNAP_VERSION
    wait: yes
    timeout: 7200
    channel: $JUJU_DEPLOY_CHANNEL
```

This will basically embed the above contents in the requesting specification
when executed. All environment variables are processed from the parent spec as
usual.
