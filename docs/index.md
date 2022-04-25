# OGC

ogc - provisioning, that's it.

# Getting Started

Welcome to the getting started guide! This should be a quick introduction to get up and running with OGC. More information on customizing and extending OGC can be found in the user documentation.

## Install

We use and recommend the use of **[Poetry](https://python-poetry.org/)**:

```shell
$ pip install poetry
$ poetry install
```

!!! caution
    If using poetry make sure to prefix running of `ogc` with the following:

    ```
    $ poetry run ogc
    ```

    Optionally, load up the virtualenv beforehand:

    ```
    $ poetry shell
    ```

Or install from [pypi](https://pypi.org):

```
$ pip install ogc
```

## Initialize

Next is to initialize the OGC environment, to do that run:

```
$ ogc init
```

It will ask you for a name, feel free to put something other than your actual name if desired.

## Provider Setup

OGC currently supports AWS and GCP out of the box (more added soon). In order for OGC to connect and deploy to these clouds a few environment variables are needed. 

Create a `.env` file in the top level directory where `ogc` is to be run:

```
AWS_ACCESS_KEY_ID=""
AWS_SECRET_ACCESS_KEY=""
AWS_REGION="us-east-2"

GOOGLE_APPLICATION_CREDENTIALS="svc.json"
GOOGLE_APPLICATION_SERVICE_ACCOUNT="..@...iam.gserviceaccount.com"
GOOGLE_PROJECT="example-project"
GOOGLE_DATACENTER="us-central1-a"
```

!!! note
    More information can be found in our [Providers](user-guide/providers.md) documentation.

## Define Provisioning

Once setup is complete, a provision specification is needed. This defines `ssh-keys` and one or more `layouts` to be provisioned. 

Create a file `ogc.yml` and place in the top level directory where `ogc` is run:

```yaml
name: ci

# SSH Keys must be passwordless
ssh-keys:
  public: ~/.ssh/id_rsa_libcloud.pub
  private: ~/.ssh/id_rsa_libcloud

layouts:
  elastic-agent-sles: 
    runs-on: sles-15
    instance-size: e2-standard-8
    username: ogc
    scripts: fixtures/ex_deploy_sles
    provider: google
    scale: 5
    remote-path: /home/ogc/ogc
    include:
      - .ogc-cache
    exclude:
      - .git
      - .venv
    artifacts: /home/ogc/output/*.xml
    tags:
      - elastic-agent-8.1.x
      - sles-gcp
```

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-8** with SUSE 15 OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

Once the specification is set, environment variables configured and a postgres database is accessible, execute a deployment in a new terminal:

```shell
$ ogc launch
```

!!! note
    If the file is something other than `ogc.yml` append the `--spec` option to the launch command:

```shell
$ ogc launch --spec my-custom-provision.yml
```

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)