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

With templating, you have the ability to query the underlying database to gather node information, a couple of modules are already exposed in the templates context:

| Var | Description |
| ----| ---- |
| db  | Exposes access to the database |
| node | Current deployed node metadata |
| env | Environment variables are made available through this key, `env['USER']` |


```bash
#!/bin/bash
<%! from ogc.templatetags import run, header, hr %>

<%namespace name="utils" file="/functions.mako"/>

${header('Connection information')}
echo "id: ${node.instance_id}"
echo "name: ${node.instance_name}"
echo "connection: ${node.layout.username}@${node.public_ip}"
echo "provider ${node.layout.provider}"
${hr()}

${run('ls', '/', l=True, h=True)}


${header('All nodes')}
% for obj in db.nodes().values():
echo "id: ${obj.instance_id}"
echo "name: ${obj.instance_name}"
echo "connection: ${obj.layout.username}@${obj.public_ip}"
echo "provider ${obj.layout.provider}"
% endfor
${header('All nodes finished')}

${run('mkdir', node.layout.remote_path + "/output", p=True)} && \
${run('touch', node.layout.remote_path + "/output/test.xml")}
```

The runtime environment is also available within the template context.

!!! note
    Any environment variables exported within OGC will be exposed in the templates.
## Reusable helpers

In the above example we reference a file called `/functions.mako` this is just another template file that sits just outside of our defined `scripts`, for example, if our `scripts` is defined to be in `scripts/my_ubuntu_deploy` then this `functions.mako` will live at `scripts/functions.mako`. 

!!! alert
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