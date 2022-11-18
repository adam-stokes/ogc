# OGC

ogc - provisioning, that's it.

# Get started

Read the [Getting Started Guide](https://adam-stokes.github.io/ogc/)

## Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/)

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

Create a file `ogc.toml` and place in the top level directory where `ogc` is run:

```toml
name = "ci"

[ssh-keys]
private = "~/.ssh/id_rsa_libcloud"
public = "~/.ssh/id_rsa_libcloud.pub"

[layouts.elastic-agent-ubuntu]
artifacts = "/home/ubuntu/output/*.xml"
exclude = [ ".git", ".venv", "artifacts" ]
extra = { }
include = [ ]
instance-size = "e2-standard-4"
ports = [ "22:22", "80:80", "443:443", "5601:5601" ]
provider = "google"
remote-path = "/home/ubuntu/ogc"
runs-on = "ubuntu-2004-lts"
scale = 1
scripts = "fixtures/ex_deploy_ubuntu"
tags = [ "elastic-agent-8-1-x", "ubuntu-gcp" ]
username = "ubuntu"
```

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-8** with Ubuntu OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

Once the specification is set, environment variables configured and a postgres database is accessible, execute a deployment in a new terminal:

```shell
$ ogc launch
```

!!! note
    If the file is something other than `ogc.toml` append the `--spec` option to the launch command:

```shell
$ ogc launch --spec my-custom-provision.toml
```

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)

# License

MIT.


