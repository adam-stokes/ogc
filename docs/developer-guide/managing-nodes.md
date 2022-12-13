# Managing Nodes Programatically

## Requirements

Accessing the functionality of OGC programatically requires that both cloud credentials and database access are configured. The environment variables for working with **AWS** or **Google** should be defined in your environment either by setting it in the `.env` or in the abscence of a dotenv file they can be exported by your current running shell.

Using the `.env` is easiest and is what we'll use for the remaining documentation, the following will configure access to both AWS and Google along with defining where our Postgres database resides:

``` sh
AWS_ACCESS_KEY_ID="abbcc"
AWS_SECRET_ACCESS_KEY="sshitsasecret"
AWS_REGION="us-east-2"

GOOGLE_APPLICATION_CREDENTIALS="mycreds.json"
GOOGLE_APPLICATION_SERVICE_ACCOUNT="bob@whodunit.iam.gserviceaccount.com"
GOOGLE_PROJECT="my-awesome-project"
GOOGLE_DATACENTER="us-central1-a"
```

## Nodes

Once the database is setup in your code, you are ready to begin creating and managing nodes. OGC provides both synchronous and asynchronous support depending on your needs.

### Launch Node

To launch a node an OGC specification is required with at least one [layout](../user-guide/defining-layouts.md) defined, create a file called `ubuntu.py`.

```python
from ogc.deployer import Deployer
from ogc.log import get_logger
from ogc.models import Layout
from ogc.provision import choose_provisioner

layout = Layout(
    instance_size="e2-standard-4",
    name="ubuntu-ogc",
    provider="google",
    remote_path="/home/ubuntu/ogc",
    runs_on="ubuntu-2004-lts",
    scale=15,
    scripts="fixtures/ex_deploy_ubuntu",
    username="ubuntu",
    ssh_private_key="~/.ssh/id_rsa_libcloud",
    ssh_public_key="~/.ssh/id_rsa_libcloud.pub",
    ports=["22:22", "80:80", "443:443", "5601:5601"],
    tags=[],
    labels=dict(
        division="engineering", org="obs", team="observability", project="perf"
    ),
)
provisioner = choose_provisioner(layout=layout)

deploy = Deployer.from_provisioner(provisioner=provisioner)
deploy.up()
deploy.exec(cmd='ls -l /')
deploy.exec_scripts()
deploy.exec_scripts(scripts='my/arbitrary/path')
deploy.down()
```

To launch this node layout:

```
$ ogc ubuntu.py
```