# OGC

ogc - provisioning, that's it.

# Get started

Read the [Getting Started Guide](https://adam-stokes.github.io/ogc/)
## Quickstart

OGC requires Postgres to function. The easiest way to fulfill this requirement is with **docker-compose**:

```yaml
version: "3.9"

services:
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
```

Bring up the services

 `$ docker-compose up`

## Install

```shell
$ pip install poetry
$ poetry install
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
## Provision and Deploy

Once the specification is set, environment variables configured and a postgres database is accessible, execute a deployment in a new terminal:

```shell
$ ogc launch
```

# License

MIT.


