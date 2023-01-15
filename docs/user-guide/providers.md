# Providers

In order to access a cloud provider, there are certain environment variables that need to be exposed for each. Each environment variable should be defined in `.env` file so it will be automatically loaded when running OGC.

## AWS

- **AWS_ACCESS_KEY_ID**
- **AWS_SECRET_ACCESS_KEY**
- **AWS_REGION**

## Google

- **GOOGLE_APPLICATION_CREDENTIALS**
- **GOOGLE_APPLICATION_SERVICE_ACCOUNT**
- **GOOGLE_PROJECT**
- **GOOGLE_DATACENTER**

### Authentication and Docker

Using `OGC` via docker is the easiest way to get started, please see this documentation on how to [setup
authentication with GCE/OGC/Docker](configuration/docker/gcloud-auth.md).