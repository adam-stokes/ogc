# Defining Layouts

Learn the layout specification and how to create your own provisioning layouts.

All layouts reside under the `layouts` key in the provision specification:

```yaml
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
    ports:
      - "80:80"
      - "443:443"
```

Each layout has a friendly name associated as seen by `elastic-agent-sles`. The next section is going to go over each option and describe its meaning.

**provider**

Define which cloud the layout will operate in. Currently supported options are **aws** and **google**.

**runs-on**

Define the base OS image to be deployed on to the nodes. The current supported list of names are:

| AWS | Google |
| ---- | ----- |
| ubuntu-2004 | ubuntu-2004 |
| ubuntu-1804 | ubuntu-1804 |
| ubuntu-1604 | ubuntu-1604 |
| sles-15 | sles-15 |
| sles-12 | sles-12 |
| sles-11 | sles-11 |
| debian-10 | debian-10 |
| debian-9 | debian-9 |
| debian-8 | debian-8 |
|| rhel-8 |
|| rhel-7 |
|| rhel-6 |


**instance-size**

Define the machine size, this is dependent on which **provider** is chosen. The **instance-size** correlates with the instance size naming for each cloud. 

For example, on AWS you would use `instance-size: c5.4xlarge` and in Google's case, `instance-size: e2-standard-8`.

**username**

The ssh user to use when deploying and accessing the nodes. This is also somewhat dependent on which **provider** is used.

In the case of **Google**, any username can be given. In the case of **AWS**, the base machines have a pre-loaded user that must be used:

| AWS    | Username |
| ------ | -------  |
| centos | centos   |
| debian | admin    |
| oracle | ec2-user |
| sles   | ec2-user |
| ubuntu | ubuntu   |
| windows[^1] | ogc     |

!!! caution
    A lot of cloud machine images disable `root` login, try to avoid using that as a user and utilize `sudo` for anything requiring elevated permissions.

**scripts**

The location on your machine where templates/scripts resides. These will be uploaded and executed during the deployment phase.

!!! note 
    See [scripting](user-guide/../scripting.md) for more information.

**scale**

How many nodes of each layout to deploy. This is also referenced during a deployment reconciliation phase.

**remote-path** (optional)

If set, any uploads/downloads outside of what's defined in `scripts` will be placed in that remote path.

**include** (optional)

A list of files/wildcards to include in the upload

**exclude** (optional)

A list of files/wildcards to exclude in the upload

**artifacts** (optional)

The remote path where script execution output is stored. This is used when pulling artifacts with `ogc pull-artifacts` and also utilized during node teardown. This will download any artifacts found into `artifacts/instance-name/`.

**tags** (optional)

Define tags for each layout, allows additional filtering capabilities and deployment options when used with `ogc ls` and `ogc exec`

**ports** (optional)

Define what ingress ports are available when accessing the node.

## Variants

OGC supports the concept of variants. In OGC's case, variants are handled by multiple provision spec files and are then merged in a merge-left fashion.

What this means is that we can take a base spec file such as:

```yaml
name: ci
ssh-keys:
  public: id_rsa.pub
  private: id_rsa

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
  elastic-agent-ubuntu: 
    runs-on: ubuntu-latest
    instance-size: e2-standard-8
    username: ogc
    scripts: fixtures/ex_deploy_ubuntu
    provider: google
    scale: 5
    remote-path: /home/ogc/ogc
    exclude:
      - .git
      - .venv
    artifacts: /home/ogc/output/*.xml
    tags:
      - elastic-agent-8.1.x
      - ubuntu-gcp
```

The name of the file doesn't matter, we'll call this file `base-spec.yml`.

Now if we need to change certain aspects of this base deploy specification we can define a second YAML file, we'll call it `ubuntu-1804-no-sles.yml`. 

In this example, let's change the `username` and `runs-on` for the **ubuntu** layout, and let's also remove the **sles** layout:

```yaml
layouts:
  elastic-agent-sles: {}
  elastic-agent-ubuntu: 
    runs-on: ubuntu-1804
    username: ubuntu
```

The merging of the specifications will remove any keys that exist if the value of the key is `{}` (signaling an empty stanza). The remaining keys that match up with the original spec will then be overridden and the rest of the specification is left untouched.

Adding new layouts is just a matter of defining another section under `layouts` in the additional spec files passed to OGC.

[^1]: This is the default user for our contributed [packer build for Windows](./windows.md)