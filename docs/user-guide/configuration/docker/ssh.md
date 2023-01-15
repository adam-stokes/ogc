{% import 'subs.j2' as subs %}
# Docker and SSH 

There's a couple of ways to handle this, the first way is to mount the ssh credentials defined in your layout to be accessible within the OGC container.

## Create a shared data volume

May be best to create a shared local data volume in docker with all the ssh keys that could be used for deployment. Then utilize docker's `--volumes-from` feature to mount the shared volume into each ogc container run.

This [DigitalOcean article](https://www.digitalocean.com/community/tutorials/how-to-share-data-between-docker-containers) is good for learning how to share volumes across containers.

## Bind mount ssh keys

Here we are telling docker to make sure our ssh keys are accessible within the containers `/root/.ssh` path.

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
        scale=9,
        scripts="fixtures/ex_deploy_ubuntu",
        username="ubuntu",
        ssh_private_key=expand_path("~/.ssh/id_rsa_libcloud"), # (1)
        ssh_public_key=expand_path("~/.ssh/id_rsa_libcloud.pub"), # (2)
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)
```

1. We are using a SSH credential that is outside of our current working directory
2. Same for our public ssh key

Since our SSH key's will not be copied in by default we'll need to tell docker how to access it:

```bash
docker run --rm -ti -v ~/.ssh/id_rsa_libcloud:/root/.ssh/id_rsa_libcloud \
    -v ~/.ssh/id_rsa_libcloud:/root/.ssh/id_rsa_libcloud \
    -v `pwd`:`pwd` \
    -w `pwd` gorambo/ogc:v4 \
    ogc fixtures/layouts/ubuntu up -v
```

## Place keys in working directory

Another simple solution is to create a ssh passwordless keypair and place it directly in your project directory. This will allow docker to copy those keys into the container during execution and made available to OGC.

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
        scale=9,
        scripts="fixtures/ex_deploy_ubuntu",
        username="ubuntu",
        ssh_private_key="fixtures/id_rsa_libcloud", 
        ssh_public_key="fixtures/id_rsa_libcloud.pub",
        ports=["22:22", "80:80", "443:443", "5601:5601"],
        tags=[],
        labels=dict(
            division="engineering", org="obs", team="observability", project="perf"
        ),
    ),
)
```

In the above example, the ssh keys are now stored in `<pwd>/fixtures`. Now running our docker container can be accomplished as follows:

{{ subs.docker_run_proper('up', from_gcloud=False) }}

??? caution
    If you keep your project in a git repo please make sure to add your ssh keys to `.gitignore`
