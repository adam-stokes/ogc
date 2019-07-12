""" Charm utilities

Api for the charmstore:
https://github.com/juju/charmstore/blob/v5/docs/API.md
"""
import requests
import yaml
import sh

cs = "https://api.jujucharms.com/v5"


def _charm_info(owner, charm, channel):
    charm_show = sh.charm.show(
        f"cs:~{owner}/{charm}", "--channel", channel, "--format", "yaml"
    )
    charm_show = yaml.safe_load(charm_show.stdout.decode())
    return charm_show


def get_manifest(entity):
    if entity.startswith("cs:"):
        entity = entity.lstrip("cs:")
    url = [cs, entity, "archive", ".build.manifest"]
    manifest = requests.get("/".join(url))
    if manifest.ok:
        return manifest.json()
    return None


def get_bundle_applications(owner, charm, channel="stable"):
    charm_show = _charm_info(owner, charm, channel)
    if charm_show and "bundle-metadata" in charm_show:
        return charm_show["bundle-metadata"]["applications"]
    return None
