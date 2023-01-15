{% import 'subs.j2' as subs %}
# Google Cloud authentication and Docker

Using a separate container for storing the Google cloud credentials we can easily target certain
commands to run with that authentication in place.

## Create Container

First, create the `gcloud-config` container:

``` bash
docker run -ti --name gcloud-config google/cloud-sdk gcloud auth login
```

This will store your credentials in the gcloud-config container volume.

## Setup authentication and environment

Download a service account credentials file from [Google](https://cloud.google.com/iam/docs/service-account) and setup the `.env` in your project root:

```bash
GOOGLE_APPLICATION_CREDENTIALS=my-google-service-creds.json
GOOGLE_APPLICATION_SERVICE_ACCOUNT=my-google@**.iam.gserviceaccount.com
GOOGLE_PROJECT=my-project
GOOGLE_DATACENTER=us-central1-a
```

## Attach container to OGC
Next, to use that with OGC, run:

{{ subs.docker_run_proper('up') }}