""" Enums
"""

from __future__ import annotations

import typing as t

LOCAL_ARTIFACT_PATH = "artifacts"
SUPPORTED_PROVIDERS = ["AWS", "GOOGLE"]

# List of tasks that can not be defined in the provision spec
RESERVED_TASKS = ["ls", "ssh"]

CLOUD_IMAGE_MAP: t.Mapping[str, t.Mapping[str, t.Mapping[str, str]]] = {
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
            "windows-2019": "ami-0587bd602f1da2f1d",
        },
    },
    "google": {
        "ubuntu-latest-lts-arm64": "ubuntu-2204-jammy-arm64-v20230429",
        "ubuntu-2204-lts-arm64": "ubuntu-2204-jammy-arm64-v20230429",
        "ubuntu-2004-lts-arm64": "ubuntu-2004-focal-arm64-v20230302",
        "ubuntu-1804-lts-arm64": "ubuntu-1804-bionic-arm64-v20230510",
        "ubuntu-latest-lts": "ubuntu-2204-jammy-v20230429",
        "ubuntu-2204-lts": "ubuntu-2204-jammy-v20230429",
        "ubuntu-2004-lts": "ubuntu-2004-focal-v20230302",
        "ubuntu-1804-lts": "ubuntu-1804-bionic-v20230510",
        "sles-latest": "sles-15-sp3-v20220223",
        "sles-15": "sles-15-sp3-v20220223",
        "debian-latest": "debian-11-bullseye-v20220317",
        "debian-10": "debian-10-buster-v20220317",
        "debian-9": "debian-9-stretch-v20220317",
    },
}
