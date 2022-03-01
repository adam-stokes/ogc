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

providers:
  aws:
    region: us-east-2

layouts:
  cluster: 
    runs-on: debian-10
    steps:
      - script: contrib/setup-deb-system
      - script: contrib/setup-docker
      - script: contrib/setup-cluster
    providers: [aws]
  elastic-agent-ubuntu:
    runs-on: ubuntu-focal
    steps:
      - run: "sudo apt update"
      - run: "sudo apt-get -qyf dist-upgrade"
    providers: [aws]
  elastic-agent-centos:
    runs-on: CentOS Stream 9
    steps:
      - script: contrib/setup-rpm-system
    providers: [aws]
  elastic-agent-sles:
    runs-on: sles-15
    steps:
      - script: contrib/setup-rpm-system
    providers: [aws]
  elastic-agent-win:
    runs-on: windows-2022
    steps:
      - script: contrib/setup-powershell-system
    providers: [aws]
```