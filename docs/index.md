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

Once setup is complete, a provision layout is needed.

Create a file `ubuntu.py`:

```python
from ogc.deployer import init
from ogc.fs import expand_path
from ogc.log import get_logger

log = get_logger("ogc")

deployment = init(
    layout_model=dict(
        instance_size="e2-standard-4",
        name="ubuntu-ogc",
        provider="google",
        remote_path="/home/ubuntu/ogc",
        runs_on="ubuntu-2004-lts",
        scale=5,
        scripts="fixtures/ex_deploy_ubuntu",
        username="ubuntu",
        ssh_private_key=expand_path("~/.ssh/id_rsa_libcloud"),
        ssh_public_key=expand_path("~/.ssh/id_rsa_libcloud.pub"),
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)
```

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-4** with Ubuntu OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

Once the specification is set, environment variables configured, execute a deployment in a new terminal:

```shell
$ ogc ubuntu.py up
$ ogc ubuntu.py exec -o cmd='sudo apt-get update && sudo apt-get dist-upgrade'
$ ogc ubuntu.py down
```

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)