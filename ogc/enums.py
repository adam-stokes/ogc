""" Enums
"""


class SpecCore:
    NAME = "name"
    IMPORT_SSH_KEYS = "import-ssh-keys"
    PROVIDERS = "providers"
    LAYOUTS = "layouts"


SPEC_CORE_LIST = [
    SpecCore.NAME,
    SpecCore.IMPORT_SSH_KEYS,
    SpecCore.PROVIDERS,
    SpecCore.LAYOUTS,
]


class SpecCoreLayout:
    RUNS_ON = "runs-on"
    USERNAME = "username"
    SCRIPTS = "scripts"
    ARCHES = "arches"
    PROVIDERS = "providers"


SPEC_CORE_LAYOUT_LIST = [
    SpecCoreLayout.RUNS_ON,
    SpecCoreLayout.USERNAME,
    SpecCoreLayout.SCRIPTS,
    SpecCoreLayout.ARCHES,
    SpecCoreLayout.PROVIDERS,
]

# list of aws owner ids for official ami images
AWS_AMI_OWNERS = {
    "ubuntu": {
        "owner_id": "099720109477",
        "prefix": "ubuntu/images/hvm-ssd/",
        "username": "ubuntu",
    },
    "debian": {
        "owner_id": "136693071363",
        "prefix": "",
        "username": "debian",
    },
    "centos": {"owner_id": "125523088429", "prefix": "", "username": "centos"},
    "sles": {
        "owner_id": "013907871322",
        "prefix": "suse-",
        "username": "ec2-user",
    },
}
