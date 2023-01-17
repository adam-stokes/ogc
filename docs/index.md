{% import 'subs.j2' as subs -%}
# OGC

ogc - provisioning, that's it.

# Getting Started

Welcome to the getting started guide! This should be a quick introduction to get up and running with OGC. More information on customizing and extending OGC can be found in the user documentation.

## Install

### Recommended

{{ subs.docker_run_proper('up') }}

??? note "SSH/GCE/Docker Authentication"
    A couple of articles to help setup ssh/gce authentication for use within docker.

    - [OGC+Docker+GCE](user-guide/configuration/docker/gcloud-auth.md) 
    - [OGC+Docker+SSH](user-guide/configuration/docker/ssh.md)
### Alternatives
We use and recommend the use of **[Poetry](https://python-poetry.org/)**:

```shell
$ pip install poetry
$ poetry install
```

??? warning "Running in Poetry"
    If using poetry make sure to prefix running of `ogc` with the following:

    ```
    $ poetry run ogc
    ```

    Optionally, load up the virtualenv beforehand:

    ```
    $ poetry shell
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

??? note "Additional Provider Information"
    More information can be found in our [Providers](user-guide/providers.md) documentation.

## Define Provisioning

Once configuration is complete, a provision layout is needed, create the following:

{{ subs.code_example(scale=5) }}

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-4** with Ubuntu OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

Once the specification is set, environment variables configured, execute a deployment in a new terminal:

### Bring up

{{ subs.docker_run_proper(task="up", hl_lines="9") }}

### Execute commands

{{ subs.docker_run_proper(task="exec", opts=["cmd='sudo apt-get update && sudo apt-get dist-upgrade'"], hl_lines="9") }}

### Bring down
{{ subs.docker_run_proper(task="down", hl_lines="9") }}

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)