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
from ogc.deployer import Deployer
from ogc.log import get_logger
from ogc.models import Layout
from ogc.provision import choose_provisioner

log = get_logger("ogc")

layout = Layout(
    instance_size="e2-standard-4",
    name="ubuntu-ogc",
    provider="google",
    remote_path="/home/ubuntu/ogc",
    runs_on="ubuntu-2004-lts",
    scale=5,
    scripts="fixtures/ex_deploy_ubuntu",
    username="ubuntu",
    ssh_private_key="~/.ssh/id_rsa_libcloud",
    ssh_public_key="~/.ssh/id_rsa_libcloud.pub",
    ports=["22:22", "80:80", "443:443", "5601:5601"],
    tags=[],
    labels=dict(
        division="engineering", org="obs", team="observability", project="perf"
    ),
)

# Alternatively
# from ogc.provisioner import GCEProvisioner
# provisioner = GCEProvisioner(layout=layout)

provisioner = choose_provisioner(layout=layout)
deploy = Deployer.from_provisioner(provisioner=provisioner)
def up(**kwargs):
    deploy.up()

def run(**kwargs):
    # pass in a directory/filepath -o path=fixtures/ubuntu
    if kwargs.get("path", None):
        deploy.exec_scripts(scripts=kwargs["path"])
    # pass in a cmd with -o cmd='ls -l /'
    elif kwargs.get("cmd", None):
        deploy.exec(kwargs["cmd"])
    else:
        deploy.exec_scripts()    

def down(**kwargs):
    deploy.down()
```

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-4** with Ubuntu OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

Once the specification is set, environment variables configured, execute a deployment in a new terminal:

```shell
$ ogc up ubuntu.py
$ ogc run ubuntu.py -o cmd='sudo apt-get update && sudo apt-get dist-upgrade'
$ ogc down ubuntu.py
```

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)