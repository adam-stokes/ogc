# Windows

OGC supports provisioning Windows instances, however, it does make a couple of assumptions:

* OpenSSH Server is running on the Windows Machine
* Rsync is installed and available
* Passwordless ssh is setup

Fortunately, we provide you with a [Packer](https://packer.io) setup that will let you 
quickly build an AWS AMI to meet those requirements.

!!! Warning
    If using OGC contributed packer build, only AWS is supported at this time.

## Build AMI

The configurations are located in [contrib/](https://github.com/adam-stokes/ogc/contrib), to get started run:

``` sh
$ git clone https://github.com/adam-stokes/ogc
$ cd ogc/contrib
```

!!! Alert
    If using these Packer configs, please note the default user to use is: `ogc`

## Windows 2019

To build a Windows 2019 Server instance run:

``` sh
ogc/contrib> $ packer build windows2019.json
```

Once complete, grab the AMI ID, as this will be used in the `layout` specification of OGC.

## Usage

To provision and deploy a Windows machine, the following example spec will work:

```toml
name = "ci"

[ssh-keys]
public = "~/.ssh/id_rsa_libcloud.pub"
private = "~/.ssh/id_rsa_libcloud"

[layouts.elastic-agent-windows]
runs-on = "ami-0587bd602f1da2f1d"
instance-size = "c5.2xlarge"
username = "ogc"
scripts = "fixtures/ex_deploy_windows"
provider = "aws"
scale = 1
remote-path = "ogc-src"
exclude = [ ".git", ".venv", "artifacts" ]
artifacts = "output\\*.xml"
tags = [ "elastic-agent-8.1.x", "windows-aws" ]
ports = [ "22:22" ]
```

Once defined, simply running:

``` sh
$ ogc launch
```

Will get you a provisioned Windows machine!

## Scripting

Powershell a good choice, works out of the box on Windows, however, if you want to use a different programming 
language the choice is yours. All the templating, database, and context is available.

For example, to print out the current node information, edit a file `01-powershell`:

```
powershell echo "${node.instance_name}:${node.public_ip}" > ${node.instance_name}.txt
```

This is a simple example, for a more advanced deployment it may be best to create 
your `ps1` files and then reference them through powershell interpreter.