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

## Create User

A single user record is required in the database, this allows OGC to track cloud resources by certain tags associated with the OGC user.

To create an initial user:

``` python
from ogc import models
from ogc.db import M, model_as_pickle

user = models.User(name=name)
with M.db.begin(write=True) as txn:
    if txn.get(user.slug.encode("ascii")):
        log.warning("OGC already setup.")
        sys.exit(1)
    txn.put(user.slug.encode("ascii"), model_as_pickle(user))
```

Querying the database uses standard [SQLAlchemy](https://sqlalchemy.org), please reference that site for additional information.

## Nodes

Once the database is setup in your code, you are ready to begin creating and managing nodes. OGC provides both synchronous and asynchronous support depending on your needs.

### Launch Node

To launch a node an OGC specification is required with at least one [layout](../user-guide/defining-layouts.md) defined.

``` python
from ogc.spec import SpecLoader

app.spec = SpecLoader.load(["/Users/adam/specs/ogc.yml"])
```

To launch this node layout synchronously:

``` python
from ogc import actions

node_ids_created = [actions.launch(layout.as_dict()) for layout in app.spec.layouts]
```

For an asynchronous version:

``` python
from ogc import actions

node_ids_created = actions.launch_async(app.spec.layouts)
```

!!! info
    The naming conventions used for async functions is to append the suffix of `async` to the synchronous function name, for example, `actions.exec` and `actions.exec_async`.

### Script Deployment

Launching and deploying are separated into two parts, this allows for further customization between bringing up a machine and letting OGC handle the remaining deployment options.

To deploy the scripts defined in your specification, use the results from the previous launch of `node_ids_created`:

``` python
script_deploy_results = actions.deploy_async(node_ids_created)
```

### Checking Results

Checking the results of the deployment can be done in this way:

``` python
if all(result == True for result in script_deploy_results):
    print("Successfully deployed")
else:
    print("One or more deployments failed")
```