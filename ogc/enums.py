""" Enums
"""

from __future__ import annotations

import typing as t

LOCAL_ARTIFACT_PATH = "artifacts"
SUPPORTED_PROVIDERS = ["AWS", "GOOGLE"]

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
