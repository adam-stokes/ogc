# OGC

ogc - provisioning, that's it.

# Getting Started

Welcome to the getting started guide! This should be a quick introduction to get up and running with OGC. More information on customizing and extending OGC can be found in the user documentation.

## Setup

OGC requires Redis and Postgres to function. The easiest way to fulfill these requirements is with **docker-compose**:

```yaml
version: "3.9"

services:
  redis:
    image: "redis:6.2-alpine"
    restart: always
    volumes:
      - "redis:/data"
    ports:
      - '6379:6379'  

  postgres:
    image: postgres:11
    environment:
      - POSTGRES_DB=ogc
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      retries: 300
      interval: 1s
    ports:
      - '5432:5432'

volumes:
  redis: {}
```

Bring up the services

 `$ docker-compose up`

**Next**, is installation of OGC. We use **[Poetry](https://python-poetry.org/)**:

```shell
$ pip install poetry==1.1.12
$ poetry install
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
    username: root
    scripts: fixtures/ex_deploy_sles
    provider: google
    scale: 5
    remote-path: /root/ogc
    include:
      - .ogc-cache
    exclude:
      - .git
      - .venv
    artifacts: /root/output/*.xml
    tags:
      - elastic-agent-8.1.x
      - sles-gcp
```

This specification tells OGC to deploy 5 nodes running on Google's **e2-standard-8** with SUSE 15 OS. 
The `scripts` section tells OGC where the template files/scripts are located that need to be uploaded to each node during the deployment phase.

## Provision and Deploy

OGC uses a client/server architecture to better handle scaling and concurrency needs. A celery server needs to be available prior launching nodes:

```shell
$ ogc server
```

*Note*: An alternative is to run this process in a separate docker container.

Once the specification is set, environment variables configured and celery is running, execute a deployment in a new terminal:

```shell
$ ogc launch
```

*Note*: If the file is something other than `ogc.yml` append the `--spec` option to the launch command:

```shell
$ ogc launch --spec my-custom-provision.yml
```

# Next steps

Learn how to manage your deployments in our [User Guide - Managing a deployment](user-guide/managing-nodes.md)