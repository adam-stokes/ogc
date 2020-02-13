[![Build Status](https://travis-ci.org/battlemidget/ogc.svg?branch=master)](https://travis-ci.org/battlemidget/ogc)

# OGC, a runner of things

ogc - task runner with a focus on deployment/testing/reporting.

## Usage

```
> pip install ogc
> ogc --spec jobs/validate/spec.yml

# Or with a ogc.yml file in same directory running ogc from
> ogc
```

```yaml

meta:
  name: Verify CK
  synopsis:
    - summary: Running the base validation suite against a deployed Kubernetes
      code: |
        # edit spec.yml and update the appropriate vars under the `env:` section
        > ogc --spec jobs/validate/spec.yml -t core
  description: |
    Verifies that CK passes integration tests
  mkdocs:
    destination:
      - "validations/ck/index.md"
    jenkins-job-builder:
      jobs:
        - jobs/ci-master.yaml
        - jobs/validate.yaml

matrix:
  snap_version:
    - 1.18/edge
    - 1.17/edge
    - 1.17/stable
    - 1.16/edge
    - 1.15/edge
  series:
    - focal
    - bionic
    - xenial
  channel:
    - edge
    - stable
  arch:
    - amd64
    - arm64

plan:
  env:
    - JUJU_DEPLOY_BUNDLE=cs:~containers/charmed-kubernetes
    - JUJU_DEPLOY_CHANNEL=$CHANNEL
    - JUJU_CLOUD=aws/us-east-1
    - JUJU_CONTROLLER=validate-ck-$SERIES
    - JUJU_MODEL=validate-model

  execute: |
    #!/bin/bash
    set -x

    if ! juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER 2>&1; then
      juju kill-controller -y $JUJU_CONTROLLER 2>&1
    fi

    juju bootstrap $JUJU_CLOUD $JUJU_CONTROLLER \
         -d $JUJU_MODEL \
         --bootstrap-series $SERIES \
         --force \
         --bootstrap-constraints arch=$ARCH \
         if [ "$SERIES" = "focal" ]; then
           --model-default image-stream=daily \
         fi
         --model-default test-mode=true \
         --model-default resource-tags=owner=k8sci

    tee overlay.yaml <<EOF> /dev/null
    applications:
      kubernetes-master:
        options:
          channel: $SNAP_VERSION
      kubernetes-worker:
        options:
          channel: $SNAP_VERSION
    EOF

    juju deploy -m $JUJU_CONTROLLER:$JUJU_MODEL \
          --overlay overlay.yaml \
          --channel $JUJU_DEPLOY_CHANNEL $JUJU_DEPLOY_BUNDLE

    juju-wait -e $JUJU_CONTROLLER:$JUJU_MODEL -w

    pytest -m "not slow" jobs/integration/validation.py \
       --cloud $JUJU_CLOUD \
       --model $JUJU_MODEL \
       --controller $JUJU_CONTROLLER


    juju destroy-controller -y --destroy-all-models --destroy-storage $JUJU_CONTROLLER
```

## More information

- [Website / Documentation](https://ogc.8op.org)
