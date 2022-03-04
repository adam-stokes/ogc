# OGC

ogc - provisioning, that's it.

## Prereqs

- Python 3.8+
- [Poetry](https://python-poetry.org/)
## Usage

```
> export AWS_ACCESS_KEY_ID=...
> export AWS_SECRET_ACCESS_KEY=..
> export AWS_REGION=us-east-2
> poetry run ogc launch --spec ci/provision.yml
```

## Example spec file

```yaml
name: ci

# SSH Keys must be passwordless
ssh-keys:
  public: ~/.ssh/id_rsa_libcloud.pub
  private: ~/.ssh/id_rsa_libcloud

layouts:
  cluster: 
    runs-on: debian-latest
    constraints: c5.4xlarge
    username: admin
    steps:
      - script: fixtures/show-metadata
      - script: contrib/setup-deb-system
      - script: contrib/setup-docker
      - script: contrib/setup-cluster
    provider: aws
  elastic-agent-ubuntu:
    runs-on: ubuntu-latest
    constraints: c5.4xlarge
    username: ubuntu
    steps:
      - run: "sudo apt update"
      - script: fixtures/show-metadata
    provider: aws
  elastic-agent-centos:
    runs-on: centos-latest
    constraints: c5.4xlarge
    username: centos
    steps:
      - script: contrib/setup-rpm-system
    provider: aws
  elastic-agent-sles:
    runs-on: sles-latest
    constraints: c5.4xlarge
    username: ec2-user
    steps:
      - script: contrib/setup-rpm-system
    provider: aws
```

## Interfacing with deployment

### List nodes

```
> poetry run ogc ls

InstanceID             Name                        Status       Connection                                                       
---------------------------------------------------------------------------------------------------------------------------------
i-0b36a26dcf08e24f6    elastic-agent-sles          running      ssh -i /Users/adam/.ssh/id_rsa_libcloud ec2-user@3.141.164.199   
---------------------------------------------------------------------------------------------------------------------------------
i-0673f1735e86fa9b0    cluster                     running      ssh -i /Users/adam/.ssh/id_rsa_libcloud admin@3.141.85.94        
---------------------------------------------------------------------------------------------------------------------------------
i-06bde64d9eaac37a0    elastic-agent-centos        running      ssh -i /Users/adam/.ssh/id_rsa_libcloud centos@3.19.30.242       
---------------------------------------------------------------------------------------------------------------------------------
i-048be62656025ee8a    elastic-agent-ubuntu        running      ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@18.222.194.224    
```

### Destroy node

```
> poetry run ogc destroy elastic-agent-sles
```

### Connect to node

```
> poetry run ogc ssh cluster
```