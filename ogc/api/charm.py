"""
charm.py - Interface to building and publishing charms

Make sure that charm environments variables are set appropriately

CHARM_BUILD_DIR, CHARM_LAYERS_DIR, CHARM_INTERFACES_DIR

See `charm build --help` for more information.

Usage:

  tox -e py36 -- python3 jobs/build-charms/charms.py build \
     --charm-list jobs/includes/charm-support-matrix.inc \
     --resource-spec jobs/build-charms/resource-spec.yaml

  tox -e py36 -- python3 jobs/build-charms/charms.py --help
"""

import os
from glob import glob
from pathlib import Path
from pprint import pformat
import click
import sh
import yaml
import time
import uuid


class CharmEnv:
    """ Charm environment
    """

    def __init__(self):
        try:
            self.build_dir = Path(os.environ.get("CHARM_BUILD_DIR"))
            self.layers_dir = Path(os.environ.get("CHARM_LAYERS_DIR"))
            self.interfaces_dir = Path(os.environ.get("CHARM_INTERFACES_DIR"))
            self.tmp_dir = Path(os.environ.get("WORKSPACE"))
        except TypeError:
            raise SystemExit(
                "CHARM_BUILD_DIR, CHARM_LAYERS_DIR, CHARM_INTERFACES_DIR, WORKSPACE: "
                "Unable to find some or all of these charm build environment variables."
            )


def log(line):
    click.echo(f"Charms :: {line}")


def push(repo_path, out_path, charm_entity, is_bundle=False):
    """ Pushes a built charm to Charmstore
    """

    log(f"vcs: {repo_path} build-path: {out_path} {charm_entity}")
    git_commit = sh.git("rev-parse", "HEAD", _cwd=repo_path)
    git_commit = git_commit.stdout.decode().strip()
    log(f"grabbing git revision {git_commit}")

    resource_args = []
    if not is_bundle:
        # Build a list of `oci-image` resources that have `upstream-source` defined,
        # which is added for this logic to work.
        resources = yaml.safe_load(
            Path(out_path).joinpath("metadata.yaml").read_text()
        ).get("resources", {})
        images = {
            name: details["upstream-source"]
            for name, details in resources.items()
            if details["type"] == "oci-image" and details.get("upstream-source")
        }
        log(f"Found {len(images)} oci-image resources:\n{pformat(images)}\n")
        for image in images.values():
            log(f"Pulling {image}...")
            sh.docker.pull(image)

        # Convert the image names and tags to `--resource foo=bar` format
        # for passing to `charm push`.
        resource_args = [
            arg
            for name, image in images.items()
            for arg in ("--resource", f"{name}={image}")
        ]

    out = sh.charm.push(out_path, charm_entity, *resource_args)
    log(f"Charm push returned: {out}")
    # Output includes lots of ansi escape sequences from the docker push,
    # and we only care about the first line, which contains the url as yaml.
    out = yaml.safe_load(out.stdout.decode().strip().splitlines()[0])
    log(f"Setting {out['url']} metadata: {git_commit}")
    sh.charm.set(out["url"], "commit={}".format(git_commit))


def pull_layers(layer_index, layer_list, layer_branch, retries=15, timeout=60):
    charm_env = CharmEnv()
    layer_list = yaml.safe_load(Path(layer_list).read_text(encoding="utf8"))
    num_runs = 0
    for layer_map in layer_list:
        layer_name = list(layer_map.keys())[0]
        if layer_name == "layer:index":
            continue

        log(layer_name)

        def download():
            for line in sh.charm(
                "pull-source", "-v", "-i", layer_index, layer_name, _iter=True
            ):
                click.echo(f" -- {line.strip()}")

        try:
            num_runs += 1
            download()
        except sh.ErrorReturnCode_1 as e:
            log(f"Problem: {e}, retrying [{num_runs}/{retries}]")
            if num_runs == retries:
                raise SystemExit(f"Could not download charm after {retries} retries.")
            time.sleep(timeout)
            download()
        ltype, name = layer_name.split(":")
        if ltype == "layer":
            sh.git.checkout("-f", layer_branch, _cwd=str(charm_env.layers_dir / name))
        elif ltype == "interface":
            sh.git.checkout(
                "-f", layer_branch, _cwd=str(charm_env.interfaces_dir / name)
            )
        else:
            raise SystemExit(f"Unknown layer/interface: {layer_name}")


def promote(charm_list, filter_by_tag, from_channel="unpublished", to_channel="edge"):
    charm_list = yaml.safe_load(Path(charm_list).read_text(encoding="utf8"))

    for charm_map in charm_list:
        for charm_name, charm_opts in charm_map.items():
            if not any(match in filter_by_tag for match in charm_opts["tags"]):
                continue

            charm_entity = f"cs:~{charm_opts['namespace']}/{charm_name}"
            click.echo(
                f"Promoting :: {charm_entity:^35} :: from:{from_channel} to: {to_channel}"
            )
            charm_id = sh.charm.show(charm_entity, "--channel", from_channel, "id")
            charm_id = yaml.safe_load(charm_id.stdout.decode())
            resources_args = []
            try:
                resources = sh.charm(
                    "list-resources",
                    charm_id["id"]["Id"],
                    channel=from_channel,
                    format="yaml",
                )
                resources = yaml.safe_load(resources.stdout.decode())
                if resources:
                    resources_args = [
                        (
                            "--resource",
                            "{}-{}".format(resource["name"], resource["revision"]),
                        )
                        for resource in resources
                    ]
            except sh.ErrorReturnCode_1:
                click.echo("No resources for {}".format(charm_id))
            sh.charm.release(
                charm_id["id"]["Id"], "--channel", to_channel, *resources_args
            )


def resource(charm_entity, channel, builder, out_path, resource_spec):
    out_path = Path(out_path)
    resource_spec = yaml.safe_load(Path(resource_spec).read_text())
    resource_spec_fragment = resource_spec.get(charm_entity, None)
    click.echo(resource_spec_fragment)
    if not resource_spec_fragment:
        raise SystemExit("Unable to determine resource spec for entity")

    os.makedirs(str(out_path), exist_ok=True)
    charm_id = sh.charm.show(charm_entity, "--channel", channel, "id")
    charm_id = yaml.safe_load(charm_id.stdout.decode())
    try:
        resources = sh.charm(
            "list-resources", charm_id["id"]["Id"], channel=channel, format="yaml"
        )
    except sh.ErrorReturnCode_1:
        click.echo("No resources found for {}".format(charm_id))
        return
    resources = yaml.safe_load(resources.stdout.decode())
    builder_sh = Path(builder).absolute()
    click.echo(builder_sh)
    for line in sh.bash(str(builder_sh), _cwd=out_path, _iter=True, _err_to_out=True):
        click.echo(line.strip())
    for line in glob("{}/*".format(out_path)):
        resource_path = Path(line)
        resource_fn = resource_path.parts[-1]
        resource_key = resource_spec_fragment.get(resource_fn, None)
        if resource_key:
            is_attached = False
            is_attached_count = 0
            while not is_attached:
                try:
                    out = sh.charm.attach(
                        charm_entity,
                        "--channel",
                        channel,
                        f"{resource_key}={resource_path}",
                        _err_to_out=True,
                    )
                    is_attached = True
                except sh.ErrorReturnCode_1 as e:
                    click.echo(f"Problem attaching resources, retrying: {e}")
                    is_attached_count += 1
                    if is_attached_count > 10:
                        raise SystemExit(
                            "Could not attach resource and max retry count reached."
                        )
            click.echo(out)


def build(
    charm_list,
    layer_list,
    layer_index,
    charm_branch,
    layer_branch,
    resource_spec,
    filter_by_tag,
    to_channel,
    dry_run,
):
    charm_env = CharmEnv()
    _charm_list = yaml.safe_load(Path(charm_list).read_text(encoding="utf8"))

    pull_layers(layer_index, layer_list, layer_branch)
    log("charm builds")
    for charm_map in _charm_list:
        for charm_name, charm_opts in charm_map.items():
            downstream = f"https://github.com/{charm_opts['downstream']}"
            if not any(match in filter_by_tag for match in charm_opts["tags"]):
                continue

            if dry_run:
                log(
                    f"{charm_name:^25} :: vcs-branch: {charm_branch} to-channel: {to_channel} tags: {','.join(charm_opts['tags'])}"
                )
                continue
            charm_entity = f"cs:~{charm_opts['namespace']}/{charm_name}"
            src_path = charm_name
            os.makedirs(src_path)

            dst_path = str(charm_env.build_dir / charm_name)
            for line in sh.git.clone(
                "--branch", charm_branch, downstream, src_path, _iter=True
            ):
                log(line)

            for line in sh.charm.build(
                r=True, force=True, _cwd=src_path, _iter=True, _err_to_out=True
            ):
                log(line.strip())
            sh.charm.proof(_cwd=dst_path)
            if not dry_run:
                push(src_path, dst_path, charm_entity)
                resource_builder = charm_opts.get("resource_build_sh", None)
                if resource_builder:
                    resource(
                        charm_entity,
                        "unpublished",
                        f"{src_path}/{resource_builder}",
                        f"{dst_path}/tmp",
                        resource_spec,
                    )
    if not dry_run:
        promote(charm_list, filter_by_tag, to_channel=to_channel)


def build_bundles(bundle_list, filter_by_tag, bundle_repo, to_channel, dry_run):
    charm_env = CharmEnv()
    _bundle_list = yaml.safe_load(Path(bundle_list).read_text(encoding="utf8"))
    log("bundle builds")
    bundle_repo_dir = charm_env.tmp_dir / "bundles-kubernetes"
    bundle_build_dir = charm_env.tmp_dir / "tmp-bundles"
    sh.rm("-rf", bundle_repo_dir)
    sh.rm("-rf", bundle_build_dir)
    os.makedirs(str(bundle_repo_dir), exist_ok=True)
    os.makedirs(str(bundle_build_dir), exist_ok=True)
    for line in sh.git.clone(bundle_repo, str(bundle_repo_dir), _iter=True):
        log(line)
    for bundle_map in _bundle_list:
        for bundle_name, bundle_opts in bundle_map.items():
            if not any(match in filter_by_tag for match in bundle_opts["tags"]):
                log(f"Skipping {bundle_name}")
                continue
            log(f"Processing {bundle_name}")
            cmd = [
                str(bundle_repo_dir / "bundle"),
                "-o",
                str(bundle_build_dir / bundle_name),
                "-c",
                to_channel,
                bundle_opts["fragments"],
            ]
            log(f"Running {' '.join(cmd)}")
            import subprocess

            subprocess.call(" ".join(cmd), shell=True)
            bundle_entity = f"cs:~{bundle_opts['namespace']}/{bundle_name}"
            log(f"Check {bundle_entity}")
            if not dry_run:
                push(
                    str(bundle_repo_dir),
                    str(bundle_build_dir / bundle_name),
                    bundle_entity,
                    is_bundle=True,
                )
    if not dry_run:
        promote(bundle_list, filter_by_tag, to_channel=to_channel)
