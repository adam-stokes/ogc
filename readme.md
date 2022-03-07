# OGC

ogc - provisioning, that's it.

## Prereqs

- Python 3.8+
- [Poetry](https://python-poetry.org/)

## Example provision file

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
## Usage

### Set environment variables
```
> export AWS_ACCESS_KEY_ID=...
> export AWS_SECRET_ACCESS_KEY=..
> export AWS_REGION=us-east-2
```

### Launch nodes

```
> poetry run ogc launch --spec ci/provision.yml
```
### List nodes

```
> poetry run ogc ls

Name                        InstanceID             Status       KeyPair           Connection                                                       
---------------------------------------------------------------------------------------------------------------------------------------------------
elastic-agent-sles          i-0c6154f78d62d3189    running      ogc-ba632446      ssh -i /Users/adam/.ssh/id_rsa_libcloud ec2-user@3.15.171.223    
---------------------------------------------------------------------------------------------------------------------------------------------------
cluster                     i-070b90d5a09fa3f41    running      ogc-53a2d728      ssh -i /Users/adam/.ssh/id_rsa_libcloud admin@18.188.119.198     
---------------------------------------------------------------------------------------------------------------------------------------------------
elastic-agent-centos        i-0687e35792343573d    running      ogc-c81f7f1f      ssh -i /Users/adam/.ssh/id_rsa_libcloud centos@13.58.247.156     
---------------------------------------------------------------------------------------------------------------------------------------------------
elastic-agent-ubuntu        i-052048090ad75a608    running      ogc-63e9bd2b      ssh -i /Users/adam/.ssh/id_rsa_libcloud ubuntu@18.217.224.189    
```
### Destroy node

```
> poetry run ogc rm --name elastic-agent-sles \
                    --name cluster \
                    --name elastic-agent-centos \
                    --name elastic-agent-ubuntu
```

### Connect to node

```
> poetry run ogc ssh cluster
```

### Upload Files and Directories

```
> poetry run ogc scp-to cluster `pwd` dst-dir
> poetry run ogc scp-to cluster readme.md readme.md
```

### List keypairs

```
> poetry run ogc ls-key-pairs --filter "my-key-prefix"
```

### Remove keypairs

```
> poetry run ogc rm-key-pairs --filter "my-key-prefix"
```

