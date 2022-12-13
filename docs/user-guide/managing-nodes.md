# Managing a Deployment

Learn how to list, inspect, access and debug your node deployments.

## Listing Nodes

To list nodes in your deployment, run the following:

```
$ ogc ls ubuntu.py
```

Which gives a table output of current node deployments:

![Listing Nodes](./assets/list_nodes.svg)


## Accessing nodes

OGC provides a helper command for easily accessing any of the nodes in your deployment.

To login to a node run:

```shell
$ ogc ssh ogc-d7cd61a7-elastic-agent-ubuntu

... ssh output ...

ogc@ogc-d7cd61a7-elastic-agent-ubuntu:~#
```

## Executing commands

Running arbitrary commands can be accomplished with:

```
$ ogc exec ubuntu.py 'ls -l /'
```

## Executing a scripts directory

In addition to running arbitrary commands, OGC can also execute a directory of templates/scripts:

```
$ ogc exec-scripts ubuntu.py fixtures/ex_deploy_ubuntu
```

This can be useful to re-run a deployment or add new functionality/one-offs to a node without disturbing the original layout specifications. Access to the database and all templating is available as well.

## Destroying nodes

OGC allows destroying of individual or a full blown cleanup. To remove a single node we run:

```
$ ogc down ubuntu.py --force
```