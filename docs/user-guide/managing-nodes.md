# Managing a Deployment

Learn how to list, inspect, access and debug your node deployments.

## Listing Nodes

To list nodes in your deployment, run the following:

```
$ ogc ls
```

Which gives a table output of current node deployments:

![Listing Nodes](./assets/list_nodes.svg)


You can further drill down with a couple of options:

To filter `by-tag` run:



```shell
$ ogc ls --by-tag user-adam
```

![Listing Nodes by Tag](./assets/list_nodes_by_tag.svg)

## Accessing nodes

OGC provides a helper command for easily accessing any of the nodes in your deployment.

To login to one of the above nodes `ogc-d7cd61a7-elastic-agent-ubuntu` run:

```shell
$ ogc ssh --by-name ogc-d7cd61a7-elastic-agent-ubuntu

... ssh output ...

ogc@ogc-d7cd61a7-elastic-agent-ubuntu:~#
```

Alternatively, use the `ID`:

```
$ ogc ssh --by-id 38
```

## Executing commands

Running arbitrary commands can be accomplished with:

```
$ ogc exec --by-name ogc-d7cd61a7-elastic-agent-ubuntu 'ls -l /'
```

Or if tags are defined, run a command across a set of machines:

```
$ ogc exec --by-tag ubuntu-gcp 'touch this_is_an_ubuntu_machine.txt'
```

## Executing a scripts directory

In addition to running arbitrary commands, OGC can also execute a directory of templates/scripts:

```
$ ogc exec-scripts --by-name ogc-d7cd61a7-elastic-agent-ubuntu fixtures/ex_deploy_ubuntu
```

Or if tags are defined, run across a set of machines:

```
$ ogc exec-scripts --by-tag ubuntu-gcp fixtures/ex_deploy_ubuntu
```

This can be useful to re-run a deployment or add new functionality/one-offs to a node without disturbing the original layout specifications. Access to the database and all templating is available as well.

## Downloading files

There are 2 ways to download files, the first is to use `ogc pull-files`, this gives you the ability to download any arbitrary files:

```
$ ogc pull-files ogc-d7cd61a7-elastic-agent-ubuntu im_on_a_computer.txt im_downloaded_computer.txt
$ stat im_downloaded_computer.txt 
16777221 24809112 -rw-r--r-- 1 adam staff 0 0 "Mar 24 11:56:24 2022" "Mar 24 11:55:16 2022" "Mar 24 11:56:24 2022" "Mar 24 11:55:16 2022" 4096 0 0 im_downloaded_computer.txt
```

Another way is if the `artifacts` key is defined in a layout. To grab files defined by that `artifacts` option run the following:

```
$ ogc pull-artifacts ogc-d7cd61a7-elastic-agent-ubuntu
```

By default, artifacts are stored in `$(pwd)/artifacts/ogc-d7cd61a7-elastic-agent-ubuntu`

```
tree artifacts/ogc-d7cd61a7-elastic-agent-ubuntu/
artifacts/ogc-d7cd61a7-elastic-agent-ubuntu/
└── test.xml

0 directories, 1 file
```

## Uploading files

OGC provides a simple way to upload arbitrary files to a node:

```
$ ogc push-files ogc-d7cd61a7-elastic-agent-ubuntu im_downloaded_computer.txt dl.txt
```

Optionally, if `--exclude` is provided, uploading files will ignore any wildcards matched. 

!!! note
    Passing multiple `--exclude` is supported and will be added to the list of excludes during upload. Useful if uploading directories and want to ignore things like `.git` and `.venv`.

## Inspecting nodes

Each action performed on a node is tracked. This allows you to quickly investigate why scripts failed. To inspect a node and see action results run:

```
$ ogc inspect --id 38
```

This will return the following output:

```
Deploy Details: ogc-d7cd61a7-elastic-agent-ubuntu
[3] Successful Actions:
                                                                                                                                                                                                                                                                                           
  (id: 90) Out: 2022-03-24 12:37:08.657289                                                                                                                                                                                                                                                 
                                                                                                                                                                                                                                                                                           
  '/usr/local/bin/pacman' -> '/usr/local/bin/pacapt'                                                                                                                                                                                                                                       
  Reading package lists...                                                                                                                                                                                                                                                                 
  Building dependency tree...                                                                                                                                                                                                                                                              
  Reading state information...                                                                                                                                                                                                                                                             
  nano is already the newest version (2.9.3-2).                                                                                                                                                                                                                                            
  nano set to manually installed.                                                                                                                                                                                                                                                          
  The following package was automatically installed and is no longer required:                                                                                                                                                                                                             
    libnuma1                                                                                                                                                                                                                                                                               
  Use 'apt autoremove' to remove it.                                                                                                                                                                                                                                                       
  0 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
```

If multiple actions exist, further drill down into the action you want (*seen here "(id: 90) Out: 2022-03-24 12:37:08." in our example*):

```
$ ogc inspect --id 38 --action-id 90
```

## Syncing a deployment

In some cases nodes will fail to deploy or you remembered you needed more than 5 nodes or maybe you need less nodes than what the original `scale` was set. 

In all these cases, OGC provides a way to keep the deployment in sync with the layouts.

To get an idea of the health of the deployment, run:

```
$ ogc status
```

The output returned will be a table displaying what's deployed, the scale, and if there are any remaining nodes left:

![Node Status Health](./assets/healthy_status.svg)

In cases where you want to add more nodes, update your layout and increase the `scale` option, in this case we want to add 10 more nodes to our `elastic-agent-sles` layout:

![Node Status Degraded](./assets/degraded_status_scale_up.svg)

Or another case where we need to reduce the number of nodes from 5 to 3:

![Node Status Degraded](./assets/degraded_status_scale_down.svg)

To perform the sync, run the following:

```
$ ogc status --reconcile
```

And the output will show OGC destroying 2 nodes from each layout:

```
2022-03-24 at 11:52:37 | INFO Reconciling: [elastic-agent-sles, elastic-agent-ubuntu]
2022-03-24 at 11:52:37 | INFO Destroying: ogc-87ba30fc-elastic-agent-sles
2022-03-24 at 11:52:37 | INFO Destroying: ogc-51b971ad-elastic-agent-sles
2022-03-24 at 11:52:37 | INFO Destroying: ogc-b3befadc-elastic-agent-ubuntu
2022-03-24 at 11:52:37 | INFO Destroying: ogc-d54a5848-elastic-agent-ubuntu
```

## Destroying nodes

OGC allows destroying of individual or a full blown cleanup. To remove a single node we run:

```
$ ogc rm --by-name ogc-d7cd61a7-elastic-agent-ubuntu --force
```

Or if we wanted to do a full teardown, run:
```
$ ogc rm-all --force
```