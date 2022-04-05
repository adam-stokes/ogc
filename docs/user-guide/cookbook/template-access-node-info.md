# Accessing node information

## Current node

In template files you have access to the node that is currently being rendered prior to those scripts being uploaded.

Below is an example of querying the current node's information and outputting it to a file:

``` sh
#!/bin/bash

echo "### CURRENT NODE" >> node_info.txt
echo "[ID: ${node.id}] Name: ${node.instance_name} || Connection: ${node.username}@${node.public_ip} || Provider: ${node.provider}" >> node_info.txt
echo "### CURRENT NODE" >> node_info.txt
```

Save this file in the location of your defined `scripts` and give it a indexed name of where in the order it should be executed, for example, `01-show-node-info`[^1].

## All nodes

In some cases you may need to grab information from another node in the deployment, for example, a second node running Kibana in which the first node needs to perform some kind of API calls against it. 

We can accomplish this using the `db` and `session` modules that's exposed in our templates. Create a file `02-curl-remote` with the following:

``` sh
#!/bin/bash
sudo pip install httpie
KIBANA_HOST=${session.query(db.Node).filter(db.Node.instance_name.contains(["kibana"]).first() or '')}

http -a username:passsword -f GET https://$KIBANA_HOST:5601/fleet/setup kbn-xsrf:ogc
```


[^1]: See the [Scripting](../scripting.md#before-starting) documentation for ordering of files.
