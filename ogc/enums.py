""" Enums
"""

PID_FILE = "ogc-server.pid"
LOCAL_ARTIFACT_PATH = "artifacts"

SUPPORTED_PROVIDERS = ["AWS", "GOOGLE"]


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
    PROVIDER = "provider"
    ARCH = "arch"


SPEC_CORE_LAYOUT_LIST = [
    SpecCoreLayout.RUNS_ON,
    SpecCoreLayout.ARCH,
    SpecCoreLayout.USERNAME,
    SpecCoreLayout.SCRIPTS,
    SpecCoreLayout.PROVIDER,
]

CLOUD_IMAGE_MAP = {
    "aws": {
        "arm64": {
            "ubuntu-2004": "ami-075c8e2e1712231db",
            "ubuntu-1804": "ami-09f78b2dda8a0dbd7",
            "centos-8": "ami-0a4c0912a6594a308",
            "sles-15": "ami-05122f5515f6f044a",
            "debian-10": "ami-06dac44ad759182bd",
        },
        "amd64": {
            "ubuntu-2004": "ami-039af3bfc52681cd5",
            "ubuntu-1804": "ami-0bd586d26693ecbe9",
            "centos-8": "ami-057cacbfbbb471bb3",
            "sles-15": "ami-0326c54d5f592764b",
            "debian-11": "ami-04dd0542609808c50",
            "debian-10": "ami-0d90bed76900e679a",
            "oracle-8": "ami-00371eeb8fd8e0e16",
        },
    },
    "google": {
        "arm64": {},
        "amd64": {
            "ubuntu-latest": "ubuntu-2004-focal-v20220325",
            "ubuntu-2004": "ubuntu-2004-focal-v20220325",
            "ubuntu-1804": "ubuntu-1804-bionic-v20220325",
            "sles-latest": "sles-15-sp3-v20220223",
            "sles-15": "sles-15-sp3-v20220223",
            "debian-latest": "debian-11-bullseye-v20220317",
            "debian-10": "debian-10-buster-v20220317",
            "debian-9": "debian-9-stretch-v20220317",
        },
    },
}
