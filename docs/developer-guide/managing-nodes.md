{% import 'subs.j2' as subs %}
# Managing Nodes Programatically

## Requirements

Accessing the functionality of OGC programatically requires that both cloud credentials and database access are configured. The environment variables for working with **AWS** or **Google** should be defined in your environment either by setting it in the `.env` or in the abscence of a dotenv file they can be exported by your current running shell.

```bash
GOOGLE_APPLICATION_CREDENTIALS="mycreds.json"
GOOGLE_APPLICATION_SERVICE_ACCOUNT="bob@whodunit.iam.gserviceaccount.com"
GOOGLE_PROJECT="my-awesome-project"
GOOGLE_DATACENTER="us-central1-a"
```

??? info "Authentication Information"
    Please read [Docker and Google Authentication](../user-guide/configuration/docker/gcloud-auth.md) for more information.

## Launch Node

Once the database is setup in your code, you are ready to begin creating and managing nodes.

To launch a node an OGC specification is required with at least one [layout](../user-guide/defining-layouts.md) defined, create a file called `ubuntu.py`.

```python
from ogc.deployer import init
from ogc.fs import expand_path
from ogc.log import get_logger

log = get_logger("ogc")

deployment = init(
    layout_model=dict(
        instance_size="e2-standard-4",
        name="ubuntu-ogc",
        provider="google",
        remote_path="/home/ubuntu/ogc",
        runs_on="ubuntu-2004-lts",
        scale=5,
        scripts="fixtures/ex_deploy_ubuntu",
        username="ubuntu",
        ssh_private_key=expand_path("~/.ssh/id_rsa_libcloud"),
        ssh_public_key=expand_path("~/.ssh/id_rsa_libcloud.pub"),
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)
```

To launch this node layout:

{{ subs.docker_run_proper('up') }}
