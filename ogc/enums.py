""" Enums
"""

PID_FILE = "ogc-server.pid"
LOCAL_ARTIFACT_PATH = "artifacts"


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
            "ubuntu-latest": "ami-075c8e2e1712231db",
            "ubuntu-2004": "ami-075c8e2e1712231db",
            "ubuntu-1804": "ami-09f78b2dda8a0dbd7",
            "centos-latest": "ami-0a4c0912a6594a308",
            "centos-8": "ami-0a4c0912a6594a308",
            "sles-latest": "ami-05122f5515f6f044a",
            "sles-15": "ami-05122f5515f6f044a",
            "debian-latest": "ami-0fd1d3db6054b3cc9",
            "debian-11": "ami-0fd1d3db6054b3cc9",
            "debian-10": "ami-06dac44ad759182bd",
        },
        "amd64": {
            "ubuntu-latest": "ami-039af3bfc52681cd5",
            "ubuntu-2004": "ami-039af3bfc52681cd5",
            "ubuntu-1804": "ami-0bd586d26693ecbe9",
            "centos-latest": "ami-057cacbfbbb471bb3",
            "centos-8": "ami-057cacbfbbb471bb3",
            "sles-latest": "ami-0326c54d5f592764b",
            "sles-15": "ami-0326c54d5f592764b",
            "debian-latest": "ami-04dd0542609808c50",
            "debian-11": "ami-04dd0542609808c50",
            "debian-10": "ami-0d90bed76900e679a",
            "windows-latest": "",
            "windows-2022": "",
            "windows-10": "",
        },
    },
    "google": {
        "arm64": {
            "ubuntu-latest": "",
            "ubuntu-2004": "",
            "ubuntu-1804": "",
            "sles-latest": "",
            "sles-15": "",
            "debian-latest": "",
            "debian-10": "",
            "debian-9": "",
        },
        "amd64": {
            "ubuntu-latest": "ubuntu-2004-focal-v20220308",
            "ubuntu-2004": "ubuntu-2004-focal-v20220308",
            "ubuntu-1804": "ubuntu-1804-bionic-v20220308",
            "sles-latest": "sles-15-sp3-v20220223",
            "sles-15": "sles-15-sp3-v20220223",
            "debian-latest": "debian-11-bullseye-v20220317",
            "debian-10": "debian-10-buster-v20220317",
            "debian-9": "debian-9-stretch-v20220317",
        },
    },
}
