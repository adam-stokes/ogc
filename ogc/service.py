""" service mapper

crude machine -> service mapper
"""

from pathlib import Path

import structlog

import ogc.db
from ogc.models.machine import MachineModel

log = structlog.getLogger()


def add(machine_model, service_name):
    """stores the machine obj and service that is running on machine"""
    registry = ogc.db.registry_path()
    services_list = [service_name]
    log.info("adding services", services=services_list, machine=machine_model.name)
    if machine_model.name in registry.iterkeys():
        services_list = ogc.db.pickle_to_model(registry[machine_model.name])
        set(services_list).add(service_name)

    registry[machine_model.name] = ogc.db.model_as_pickle(services_list)
