# Upgrading OGC

Upgrades should be relatively easy, the only item to be careful of is the database. OGC tries to keep database changes to a minimum, however, in some cases it is unavoidable and the database schema needs to be updated.

This will effect users who:

* Have an active deployment which means objects stored in the database
* Upgraded OGC from a previous version without tearing down the known deployments

To help with the upgrade process, OGC provides a cli command to update your current database schema. Once OGC is upgraded to a new version run the following:

``` sh
$ ogc db-migrate
```

This will sync up your current database with the latest schema from OGC.

!!! note
    Only when the database schema changes will you need to run this. Communication about database changes will be made in the release notes.