{% import 'subs.j2' as subs %}

# Docker and SSH 

There's a couple of ways to handle this, the first way is to mount the ssh credentials defined in your layout to be accessible within the OGC container.

## Create a shared data volume

May be best to create a shared local data volume in docker with all the ssh keys that could be used for deployment.

### Create shared volume

Create a shared volume called `ssh-creds`

```bash
docker volume create ssh-creds
```

### Generate SSH Keys

```bash
docker run -ti --rm -v ssh-creds:/ssh ubuntu
ubuntu-docker> apt-get update && apt-get install -qyf openssh-client
ubuntu-docker> ssh-keygen -t ed25519 -C youremail.com
```

When prompted, store your credentials in `/ssh/id_ed25519`

### Run with new keys

Once complete, you can mount that shared volume going forward to have access to your ssh keys in the ogc executed container.

```bash
docker run --env-file .env \
    --rm \
    --volumes-from gcloud-config \
    -v ssh-creds:/root/.ssh \
    -v `pwd`:`pwd` -w `pwd` \
    -it ogc:latest \
    ogc ubuntu.py up -v
```

Your example layout would look like:

{{ subs.code_example(ssh_path="~/ssh/id_ed25519", hl_lines="13 14") }}

This [DigitalOcean article](https://www.digitalocean.com/community/tutorials/how-to-share-data-between-docker-containers) is good for learning how to share volumes across containers.

## Bind mount ssh keys

Here we are telling docker to make sure our ssh keys are accessible within the containers `/root/.ssh` path.

{{ subs.code_example(hl_lines="13 14") }}

Since our SSH key's will not be copied in by default we'll need to tell docker how to access it:

```bash
docker run --rm -ti \
    -v ~/.ssh/id_rsa_libcloud:/root/.ssh/id_rsa_libcloud \
    -v ~/.ssh/id_rsa_libcloud.pub:/root/.ssh/id_rsa_libcloud.pub \
    -v `pwd`:`pwd` \
    -w `pwd` gorambo/ogc:v4 \
    ogc ubuntu.py up -v
```

## Place keys in working directory

Another simple solution is to create a ssh passwordless keypair and place it directly in your project directory. This will allow docker to copy those keys into the container during execution and made available to OGC.

{{ subs.code_example(ssh_path="fixtures/id_rsa_libcloud", hl_lines="13 14") }}

In the above example, the ssh keys are now stored in `<pwd>/fixtures`. Now running our docker container can be accomplished as follows:

{{ subs.docker_run_proper('up', from_gcloud=False) }}

??? caution
    If you keep your project in a git repo please make sure to add your ssh keys to `.gitignore`
