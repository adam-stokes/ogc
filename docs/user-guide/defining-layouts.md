# Defining Layouts

Learn the layout specification and how to create your own provisioning layouts.

All layouts reside under the `layouts` key in the provision specification:

```
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

Each layout has a friendly name associated as seen by `elastic-agent-sles`. The next section is going to go over each option and describe its meaning.

**provider**

Define which cloud the layout will operate in. Currently supported options are **aws** and **google**.

**runs-on**

Define the base OS image to be deployed on to the nodes. The current supported list of names are:

| AWS | Google |
| ---- | ----- |
| ubuntu-latest | ubuntu-latest |
| ubuntu-2004   | ubuntu-2004 |
| ubuntu-1804 | ubuntu-1804 |
| centos-latest | sles-latest |
| centos-8 | sles-15 |
| sles-latest | debian-latest |
| sles-15 | debian-10 |
| debian-latest | debian-9 |
| debian-11 | |
| debian-10 | |

**instance-size**

Define the machine size, this is dependent on which **provider** is chosen. The **instance-size** correlates with the instance size naming for each cloud. 

For example, on AWS you would use `instance-size: c5.4xlarge` and in Google's case, `instance-size: e2-standard-8`.

**username**

The ssh user to use when deploying and accessing the nodes. This is also somewhat dependent on which **provider** is used.

In the case of **Google**, any username can be given. In the case of **AWS**, the base machines have a pre-loaded user that must be used:

| AWS | Username |
| ---- | ------- |
| ubuntu | ubuntu |
| centos | ec2-user |
| debian | admin |

**scripts**

The location on your machine where templates/scripts resides. These will be uploaded and executed during the deployment phase.

*Note*: See [scripting](user-guide/../scripting.md) for more information.

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