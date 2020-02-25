#!/bin/bash
set -eux

setup_env()
{
    pwd
  echo "JUJU-CONTROLLER-$(ogc-collect get-key job_id | cut -f1 -d-)"
}
