# OGC

ogc - provisioning, that's it.

## Usage

```
> pip install ogc
> ogc --spec ci/provision.yml

# Or with a ogc.yml file in same directory running ogc from
> ogc
```

## Example spec file

```yaml
name: ci

providers:
  aws:
    region: us-east-1
  google:
    region: us-east-1
    project: my-google-project

layout:
  cluster: 
    runs-on: ubuntu-latest
    username: ubuntu
    scripts:
      - contrib/setup-deb-system
      - contrib/setup-docker
      - contrib/setup-cluster
  elastic-agent-ubuntu:
    runs-on: ubuntu-latest
    username: ubuntu
    scripts:
      - contrib/setup-deb-system
    arches: [amd64, arm64]
  elastic-agent-centos:
    runs-on: centos-latest
    username: admin
    scripts:
      - contrib/setup-rpm-system
    arches: [amd64, arm64]
    clouds: [aws]
  elastic-agent-win:
    runs-on: windows-latest
    scripts:
      - contrib/setup-powershell-system
    arches: [amd64]
    clouds: [aws]
```