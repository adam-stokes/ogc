# Google Cloud authentication and Docker

Using a separate container for storing the Google cloud credentials we can easily target certain
commands to run with that authentication in place.

## Create Container

First, create the `gcloud-config` container:

``` bash
docker run -ti --name gcloud-config google/cloud-sdk gcloud auth login
```

This will store your credentials in the gcloud-config container volume.

This volume should only mounted with containers you want to have access to your credentials, which probably won't be anything that's not cloud-sdk

## Attach container to OGC
Next, to use that with OGC, run:

``` bash
docker run --rm -ti --volumes-from gcloud-config ogc:latest ogc fixtures/layouts/ubuntu up -v
```