# OGC

ogc - provisioning, that's it.

## Prereqs

- Python 3.8+
- [Poetry](https://python-poetry.org/)
## Usage

```
> export AWS_ACCESS_KEY_ID=...
> export AWS_SECRET_ACCESS_KEY=..
> poetry run ogc --spec ci/provision.yml

# Or with a ogc.yml file in same directory running ogc from
> poetry run ogc
```

## Example spec file

```yaml
name: ci

# SSH Keys must be generated in PEM format
# ssh-keygen -m PEM
ssh-keys:
  public: ~/.ssh/id_rsa_libcloud.pub
  private: ~/.ssh/id_rsa_libcloud

# Configure the provider parameters here, they will
# be referenced by each layout during deployment.
providers:
  aws:
    region: us-east-2

layouts:
  cluster: 
    runs-on: ami-0d90bed76900e679a
    constraints: c5.4xlarge
    username: admin
    steps:
      - script: contrib/setup-deb-system
      - script: contrib/setup-docker
      - script: contrib/setup-cluster
    provider: aws
  elastic-agent-ubuntu:
    runs-on: ami-039af3bfc52681cd5
    constraints: c5.4xlarge
    username: ubuntu
    steps:
      - run: "sudo apt update"
    provider: aws
  elastic-agent-centos:
    runs-on: ami-057cacbfbbb471bb3
    constraints: c5.4xlarge
    username: centos
    steps:
      - script: contrib/setup-rpm-system
    provider: aws
  elastic-agent-sles:
    runs-on: ami-0f7cb53c916a75006
    constraints: c5.4xlarge
    username: ec2-user
    steps:
      - script: contrib/setup-rpm-system
    provider: aws
  elastic-agent-win:
    runs-on: windows-2022
    constraints: cores=16 mem=8G disk=100G
    steps:
      - script: contrib/setup-powershell-system
    provider: google
```