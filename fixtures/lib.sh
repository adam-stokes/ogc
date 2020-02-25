#!/bin/bash
set -eux

setup_env()
{
    JUJU_CONTROLLER="JUJU-CONTROLLER-$(ogc-collect get-key job_id | cut -f1 -d-)"

    ogc-collect set-key "juju_controller" "$JUJU_CONTROLLER"
    ogc-collect set-key "booya" "hidyho"
}
