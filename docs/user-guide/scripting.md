# Scripting

All deployments have the ability to execute scripts once a node becomes available.

## Before starting

A couple of things to keep in mind:

- All scripts are executed in order based on the filenames. It is recommended to create scripts with a numbered prefix, for example:

```
- scripts/
  -  01-install-deps
  -  02-configure-services
```

- There is a special reserved filename `teardown`, if this file exists it will only be executed during a removal of a node. This is useful for any cleanup actions that may need to be run, such as removing test users, un-enrolling from a service, etc.

## Writing scripts

Scripts can be written in any language, it is up to you to configure the nodes so that any runtimes and library dependencies are met on the target node for your script to execute in. 

One way to accomplish this is to create `01-setup-env` bash script:

```bash
#!/bin/bash

echo "Installing python3 on ubuntu"
sudo apt-get update
sudo apt-get install -qyf python3
sudo pip install sh
```

Then in subsequent scripts, using **python3** is available. For example, in file `02-run-cmd-in-python`:

```python
#!/usr/bin/env python3

import sh

sh.ls('/')
sh.cp('-a', 'mydir', 'anotherdir')
```

## Templating

OGC provides some additional capabilities through templating. Under the hood [python-mako](https://www.makotemplates.org/) is used for the parsing.

With templating, you have the ability to query the underlying database to gather node information. Because mako supports the importing of python modules and our OGC environment is already exposed, we can access our `db` module and use some helper methods.

```bash
#!/bin/bash
<%namespace name="db" module="ogc.db"/>

echo ""
% for node in db.by_tag('sles'):
echo "[ID: ${node.id}] Name: ${node.instance_name} || Connection: ${node.username}@${node.public_ip} || Provider: ${node.provider}"
% endfor
echo ""
```

The runtime environment is also available within the template context. In one example, we can export the following into our `.env` file and reference those in the templates:

- **OGC_ELASTIC_AGENT_VERSION**
- **OGC_ELASTIC_AGENT_SHA**
- **OGC_ELASTIC_AGENT_VERSION**
- **OGC_FLEET_URL**
- **OGC_FLEET_ENROLLMENT_TOKEN** 

See the below example for downloading elastic-agent and enrolling it into a fleet server. The variable exposed to all templates for accessing the environment variables is `env`

```bash
#!/bin/bash
<%namespace name="utils" file="/functions.mako"/>

<%
url = "https://staging.elastic.co/%s-%s/downloads/beats/elastic-agent/elastic-agent-%s-linux-x86_64.tar.gz" % (env['OGC_ELASTIC_AGENT_VERSION'], env['OGC_ELASTIC_AGENT_SHA'], env['OGC_ELASTIC_AGENT_VERSION'])
%>
${utils.setup_env()}
${utils.install_pkgs(['nano'])}
${utils.download(url, 'elastic-agent.tar.gz')}
${utils.extract('elastic-agent.tar.gz')}

mv elastic-agent-${env['OGC_ELASTIC_AGENT_VERSION']}-linux-x86_64 elastic-agent

cd elastic-agent && ./elastic-agent install -f --url=${env['OGC_FLEET_URL']} --enrollment-token=${env['OGC_FLEET_ENROLLMENT_TOKEN']}
```

### Resuable helpers

In the above example we reference a file called `/functions.mako` this is just another template file that sits just outside of our defined `scripts`, for example, if our `scripts` is defined to be in `scripts/my_ubuntu_deploy` then this `functions.mako` will live at `scripts/functions.mako`. 

This is good practice as you may have multiple layouts with different script directories for each and would like to store common functionality in a single place.

Defining helper functions is straight forward, lets look at `functions.mako` for an example:

```bash
## Helper template functions downloading/extracting files
<%def name="setup_env()">
if ! test -f "/usr/local/bin/pacapt"; then
    wget -O /usr/local/bin/pacapt https://github.com/icy/pacapt/raw/ng/pacapt
    chmod 755 /usr/local/bin/pacapt
    ln -sv /usr/local/bin/pacapt /usr/local/bin/pacman || true
fi
</%def>

<%def name="install_pkgs(pkgs)">
% for pkg in pkgs:
pacapt install --noconfirm ${pkg}
% endfor
</%def>

<%def name="download(url, src_file)">
wget -O ${src_file} ${url}
</%def>

<%def name="extract(src, dst=None)">
% if dst:
mkdir -p ${dst}
tar -xvf ${src} -C ${dst}
% else:
tar -xvf ${src}
% endif
</%def>
```

Each `%def` section defines a function block that when called with any necessary arguments will output that data into the scripts with all necessary translations handled.

You can see the usage of these functions in the previous example for installing elastic-agent.

It is worth the time to visit Mako's website and learn about its feature set, particularly [namespaces](https://docs.makotemplates.org/en/latest/namespaces.html) and [defs and blocks](https://docs.makotemplates.org/en/latest/defs.html).