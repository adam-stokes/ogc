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

CLOUD_IMAGE_MAP = {
    "aws": {
        "ubuntu-latest": "ami-039af3bfc52681cd5",
        "ubuntu-latest-arm": "ami-075c8e2e1712231db",
        "ubuntu-2004": "ami-039af3bfc52681cd5",
        "ubuntu-2004-arm": "ami-075c8e2e1712231db",
        "ubuntu-1804": "ami-0bd586d26693ecbe9",
        "ubuntu-1804-arm": "ami-09f78b2dda8a0dbd7",
        "centos-latest": "ami-057cacbfbbb471bb3",
        "centos-latest-arm": "ami-0a4c0912a6594a308",
        "centos-8": "ami-057cacbfbbb471bb3",
        "centos-8-arm": "ami-0a4c0912a6594a308",
        "sles-latest": "ami-0326c54d5f592764b",
        "sles-latest-arm": "ami-05122f5515f6f044a",
        "sles-15": "ami-0326c54d5f592764b",
        "sles-15-arm": "ami-05122f5515f6f044a",
        "debian-latest": "ami-04dd0542609808c50",
        "debian-latest-arm": "ami-0fd1d3db6054b3cc9",
        "debian-11": "ami-04dd0542609808c50",
        "debian-11-arm": "ami-0fd1d3db6054b3cc9",
        "debian-10": "ami-0d90bed76900e679a",
        "debian-10-arm": "ami-06dac44ad759182bd",
        "windows-latest": "",
        "windows-2022": "",
        "windows-10": "",
    },
    "google": {
        "ubuntu-latest": "",
        "ubuntu-latest-arm" "ubuntu-2004": "",
        "ubuntu-2004-arm": "",
        "ubuntu-1804": "",
        "ubuntu-1804-arm": "",
        "centos-latest": "",
        "centos-latest-arm": "",
        "centos-9": "",
        "centos-9-arm": "",
        "centos-8": "",
        "centos-8-arm": "",
        "sles-latest": "",
        "sles-latest-arm": "",
        "sles-15": "",
        "sles-15-arm": "",
        "debian-latest": "",
        "debian-latest-arm": "",
        "debian-10": "",
        "debian-10-arm": "",
        "debian-9": "",
        "debian-9-arm": "",
        "windows-latest": "",
        "windows-2022": "",
        "windows-10": "",
    },
}
