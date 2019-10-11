[![Build Status](https://travis-ci.org/battlemidget/ogc.svg?branch=master)](https://travis-ci.org/battlemidget/ogc)

# OGC, a runner of things

ogc - task runner with a focus on deployment/testing/reporting.

## Description

OGC is powered by plugins that can be discovered on https://pypi.org with the
prefix of `ogc-plugins`. With plugins installed different aspects of a run can
be defined through a spec file, which is a yaml file setting up plugin
configuration for the particular goal.

## Usage

```
> pip install ogc
> ogc --spec jobs/validate/spec.yml --tag core

# Or with a ogc.yml file in same directory running ogc from
> ogc
```

## Add plugins

To make *OGC* a bit more useful, install a few plugins:

```
> pip install ogc-plugins-juju
```

This will allow you to add functionality such as running scripts and preparing
environment variables. Please see the plugins section of the docs for more
information.

```yaml

meta:
  name: Validate Charmed Kubernetes
  description: |
    Runs validation test suite against a vanilla deployment of Charmed Kubernetes
  mkdocs:
    destination: validations/ck/index.md

plan:
  - &BASE_JOB
    env:
      - SNAP_VERSION=1.16/edge
      - JUJU_DEPLOY_BUNDLE=cs:~containers/charmed-kubernetes
      - JUJU_DEPLOY_CHANNEL=edge
      - JUJU_CLOUD=aws/us-east-2
      - JUJU_CONTROLLER=validate-ck
      - JUJU_MODEL=validate-model
    install:
      - pip install -rrequirements.txt
      - pip install -rrequirements_test.txt
      - pip install git+https://github.com/juju/juju-crashdump.git
      - sudo apt install -qyf build-essential
      - sudo snap install charm --edge --classic
      - sudo snap install juju --classic
    before-script:
      - juju:
          cloud: $JUJU_CLOUD
          controller: $JUJU_CONTROLLER
          model: $JUJU_MODEL
          bootstrap:
            debug: no
            model-default:
              - test-mode=true
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
            channel: $JUJU_DEPLOY_CHANNEL
    script:
      - |
        #!/bin/bash
        set -eux
        pytest jobs/integration/validation.py \
             --cloud $JUJU_CLOUD \
             --controller $JUJU_CONTROLLER \
             --model $JUJU_MODEL
    after-script:
      - juju-crashdump -a debug-layer -a config -m $JUJU_CONTROLLER:$JUJU_MODEL
      - aws s3 sync *.log s3://jenkaas/$JUJU_DEPLOY_BUNDLE/$SNAP_VERSION
      - aws s3 sync juju-crashdump* s3://jenkaas/$JUJU_DEPLOY_BUNDLE/$SNAP_VERSION
      - juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER
    tags: [core]
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.15/edge
      - JUJU_DEPLOY_BUNDLE=charmed-kubernetes
    tags: [core]
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.14/edge
      - JUJU_DEPLOY_BUNDLE=charmed-kubernetes
    tags: [core]
  - <<: *BASE_JOB
    env:
      - JUJU_DEPLOY_BUNDLE=charmed-kubernetes
      - SNAP_VERSION=1.13/edge
    tags: [core]
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.16/edge
      - JUJU_DEPLOY_BUNDLE=kubernetes-calico
    tags: [calico]
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.15/edge
      - JUJU_DEPLOY_BUNDLE=kubernetes-calico
    tags: [calico]
  - <<: *BASE_JOB
    env:
      - SNAP_VERSION=1.14/edge
      - JUJU_DEPLOY_BUNDLE=kubernetes-calico
    tags: [calico]
  - <<: *BASE_JOB
    env:
      - JUJU_DEPLOY_BUNDLE=kubernetes-calico
      - SNAP_VERSION=1.13/edge
    tags: [calico]
```

## More information

- [Website / Documentation](https://ogc.8op.org)
