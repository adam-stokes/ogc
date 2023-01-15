{% import 'subs.j2' as subs %}
# Managing a Deployment

Learn how to list, inspect, access and debug your node deployments.

??? caution "Assumptions"
    This assumes you've created a layout in a file named `ubuntu.py` and you have `.env` plus Google Authentication completed.

## Listing Nodes

To list nodes in your deployment, run the following:

{{ subs.docker_run_proper('ls') }}

Which gives a table output of current node deployments:

![Listing Nodes](./assets/list_nodes.svg)


## Accessing nodes

OGC provides a helper command for easily accessing any of the nodes in your deployment.

To login to a node run:

{{ subs.docker_run_proper('ssh', opts=['instance_id=123432432']) }}

Or

{{ subs.docker_run_proper('ssh', opts=['instance_name=ogc-ubuntu-001']) }}

## Executing commands

Running arbitrary commands can be accomplished with:

{{ subs.docker_run_proper('exec', opts=["cmd='ls -l /"]) }}

## Executing a scripts directory

In addition to running arbitrary commands, OGC can also execute a directory of templates/scripts:

{{ subs.docker_run_proper('exec_scripts', opts=['scripts=fixtures/ex_deploy_ubuntu']) }}

This can be useful to re-run a deployment or add new functionality/one-offs to a node without disturbing the original layout specifications. Access to the database and all templating is available as well.

## Destroying nodes

OGC allows destroying of individual or a full blown cleanup. To remove a single node we run:

{{ subs.docker_run_proper('down', opts=['instance_name=ogc-ubuntu-001']) }}
