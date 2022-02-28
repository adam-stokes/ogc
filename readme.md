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
    runs-on: ubuntu-latest
    scripts:
      - contrib/setup-deb-system
      - contrib/setup-docker
      - contrib/setup-cluster
    providers: [google]
  elastic-agent-ubuntu:
    runs-on: ubuntu-latest
    scripts:
      - contrib/setup-deb-system
    arches: [amd64, arm64]
  elastic-agent-centos:
    runs-on: centos-latest
    scripts:
      - contrib/setup-rpm-system
    arches: [amd64, arm64]
    providers: [google]
  elastic-agent-win:
    runs-on: windows-latest
    scripts:
      - contrib/setup-powershell-system
    arches: [amd64]
    providers: [google]
```