"""
snaps-source.py - Building snaps from source and promoting them to snapstore

"""
from .. import lp, idm, git
from .. import snap as snapapi
from jinja2 import Template
from pathlib import Path
from pymacaroons import Macaroon
from urllib.parse import urlparse
import click
import glob
import operator
import os
import re
import semver
import sh
import sys
import yaml


def _render(tmpl_file, context):
    """ Renders a jinja template with context
    """
    template = Template(tmpl_file.read_text(), keep_trailing_newline=True)
    return template.render(context)


def sync_upstream(snap_list, starting_ver="1.13.7"):
    """ Syncs the upstream k8s release tags with our snap branches

    Usage:
    snaps-source.py sync-upstream --snap-list includes/k8s-snap-list.inc
    """
    env = os.environ.copy()
    supported_releases = []
    upstream_releases = git.remote_tags("https://github.com/kubernetes/kubernetes")

    for rel in upstream_releases:
        _fmt_rel = rel[1:]
        try:
            semver.parse(_fmt_rel)
            if semver.compare(_fmt_rel, starting_ver) >= 0:
                supported_releases.append(rel)
        except:
            click.echo(f"Skipping invalid version: {rel}")

    snaps = yaml.safe_load(Path(snap_list).read_text(encoding="utf8"))
    for snap in snaps:
        click.echo(f"Checking: git+ssh://cdkbot@git.launchpad.net/snap-{snap}")
        git_repo = f"git+ssh://cdkbot@git.launchpad.net/snap-{snap}"
        snap_releases = git.remote_branches(git_repo)
        if not set(supported_releases).issubset(set(snap_releases)):
            for snap_rel in set(supported_releases).difference(set(snap_releases)):
                click.echo(f"Creating branch for {snap}-{snap_rel}")
                _create_branch(git_repo, "master", snap_rel, dry_run=False)
                _fmt_version = semver.parse(snap_rel[1:])
                _fmt_version = f'{_fmt_version["major"]}.{_fmt_version["minor"]}'
                click.echo(f"Generating recipe for {snap}-{_fmt_version}")
                _create_snap_recipe(
                    snap=snap,
                    version=_fmt_version,
                    track=f"{_fmt_version}/edge",
                    owner="k8s-jenkaas-admins",
                    tag=snap_rel,
                    repo=git_repo,
                    dry_run=False,
                    snap_recipe_email=os.environ.get("K8STEAMCI_USR"),
                    snap_recipe_password=os.environ.get("K8STEAMCI_PSW"),
                )


def create_branches(repo_list, from_branch, to_branch, dry_run):
    """ Creates a git branch based on the list of  upstream snap repo and a version to branch as. This will also update
    the snapcraft.yaml with the correct version to build the snap from in that particular branch.

    These branches must already exist in https://github.com/kubernetes/kubernetes.

    Usage:

    ogc snap create-branches --repo git+ssh://lp_git_user@git.launchpad.net/snap-kubectl \
      --from-branch master \
      --to-branch 1.16.0-alpha.0
    """
    for repo in repo_list:
       create_branch(repo, from_branch, to_branch, dry_run)


def create_branch(repo, from_branch, to_branch, dry_run):
    """ Creates a git branch based on the upstream snap repo and a version to branch as. This will also update
    the snapcraft.yaml with the correct version to build the snap from in that particular branch.

    These branches must already exist in https://github.com/kubernetes/kubernetes.

    Usage:

    ogc snap create-branch --repo git+ssh://lp_git_user@git.launchpad.net/snap-kubectl \
      --from-branch master \
      --to-branch 1.16.0-alpha.0
    """
    env = os.environ.copy()

    if git.branch_exists(repo, to_branch, env):
        click.echo(f"{to_branch} already exists, skipping...")
        sys.exit(0)

    snap_basename = urlparse(repo)
    snap_basename = Path(snap_basename.path).name
    if snap_basename.endswith(".git"):
        snap_basename = snap_basename.rstrip(".git")
    sh.rm("-rf", snap_basename)
    sh.git.clone(repo, branch=from_branch, _env=env)
    sh.git.config("user.email", "cdkbot@gmail.com", _cwd=snap_basename)
    sh.git.config("user.name", "cdkbot", _cwd=snap_basename)
    sh.git.checkout("-b", to_branch, _cwd=snap_basename)

    snapcraft_fn = Path(snap_basename) / "snapcraft.yaml"
    snapcraft_fn_tpl = Path(snap_basename) / "snapcraft.yaml.in"
    if not snapcraft_fn_tpl.exists():
        click.echo(f"{snapcraft_fn_tpl} not found")
        sys.exit(1)
    snapcraft_yml = snapcraft_fn_tpl.read_text()
    snapcraft_yml = _render(snapcraft_fn_tpl, {"snap_version": to_branch.lstrip("v")})
    snapcraft_fn.write_text(snapcraft_yml)

    if not dry_run:
        sh.git.add(".", _cwd=snap_basename)
        sh.git.commit("-m", f"Creating branch {to_branch}", _cwd=snap_basename)
        sh.git.push(repo, to_branch, _cwd=snap_basename, _env=env)


def branch(repo, from_branch, to_branch, dry_run):
    return create_branch(repo, from_branch, to_branch, dry_run)


def create_snap_recipe(
    snap,
    version,
    track,
    owner,
    tag,
    repo,
    dry_run,
    snap_recipe_email,
    snap_recipe_password,
):
    """ Creates an new snap recipe in Launchpad

    snap: Name of snap to create the recipe for (ie, kubectl)
    version: snap version channel apply this too (ie, Current patch is 1.13.3 but we want that to go in 1.13 snap channel)
    track: snap store version/risk/branch to publish to (ie, 1.13/edge/hotfix-LP123456)
    owner: launchpad owner of the snap recipe (ie, k8s-jenkaas-admins)
    tag: launchpad git tag to pull snapcraft instructions from (ie, git.launchpad.net/snap-kubectl)
    repo: launchpad git repo (git+ssh://$LPCREDS@git.launchpad.net/snap-kubectl)

    # Note: this account would need access granted to the snaps it want's to publish from the snapstore dashboard
    snap_recipe_email: snapstore email for being able to publish snap recipe from launchpad to snap store
    snap_recipe_password: snapstore password for account being able to publish snap recipe from launchpad to snap store

    Usage:

    ogc snap create-snap-recipe --snap kubectl --version 1.13 --tag v1.13.2 \
      --track 1.13/edge/hotfix-LP123456 \
      --repo git+ssh://$LPCREDS@git.launchpad.net/snap-kubectl \
      --owner k8s-jenkaas-admins \
      --snap-recipe-email myuser@email.com \
      --snap-recipe-password aabbccddee

    """
    _client = lp.Client(stage="production")
    _client.login()

    params = {
        "name": snap,
        "owner": owner,
        "version": version,
        "branch": tag,
        "repo": repo,
        "track": [track],
    }

    click.echo(f"  > creating recipe for {params}")
    if dry_run:
        click.echo("dry-run only, exiting.")
        sys.exit(0)
    snap_recipe = _client.create_or_update_snap_recipe(**params)
    caveat_id = snap_recipe.beginAuthorization()
    cip = idm.CanonicalIdentityProvider(
        email=snap_recipe_email, password=snap_recipe_password
    )
    discharge_macaroon = cip.get_discharge(caveat_id).json()
    discharge_macaroon = Macaroon.deserialize(discharge_macaroon["discharge_macaroon"])
    snap_recipe.completeAuthorization(discharge_macaroon=discharge_macaroon.serialize())
    snap_recipe.requestBuilds(archive=_client.archive(), pocket="Updates")


def _alias(match_re, rename_re, snap):
    """ Provide any snap substitutions for things like kubectl-eks...snap

    Usage:

      alias = _rename(match_re\'(?=\\S*[-]*)([a-zA-Z-]+)(.*)\',
                      rename-re=\'\\1-eks_\\2\',
                      snap=kubectl)
    """
    click.echo(f"Setting alias based on {match_re} -> {rename_re}: {snap}")
    return re.sub(match_re, fr"{rename_re}", snap)


def _set_snap_alias(build_path, alias):
    click.echo(f"Setting new snap alias: {alias}")
    if build_path.exists():
        snapcraft_yml = yaml.load(build_path.read_text())
        if snapcraft_yml["name"] != alias:
            snapcraft_yml["name"] = alias
            build_path.write_text(
                yaml.dump(snapcraft_yml, default_flow_style=False, indent=2)
            )


def build(snap, build_path, version, arch, match_re, rename_re, dry_run):
    """ Build snaps

    Usage:

    ogc snap build --snap kubectl --snap kube-proxy --version 1.10.3 --arch amd64 --match-re '(?=\S*[-]*)([a-zA-Z-]+)(.*)' --rename-re '\1-eks'

    Passing --rename-re and --match-re allows you to manipulate the resulting
    snap file, for example, the above renames kube-proxy_1.10.3_amd64.snap to
    kube-proxy-eks_1.10.3_amd64.snap
    """
    if not version.startswith("v"):
        version = f"v{version}"
    env = os.environ.copy()
    env["KUBE_VERSION"] = version
    env["KUBE_ARCH"] = arch
    sh.git.clone(
        "https://github.com/juju-solutions/release.git",
        build_path,
        branch="rye/snaps",
        depth="1",
    )
    build_path = Path(build_path) / "snap"
    snap_alias = None

    for _snap in snap:
        if match_re and rename_re:
            snap_alias = _alias(match_re, rename_re, _snap)

        if snap_alias:
            snapcraft_fn = build_path / f"{_snap}.yaml"
            _set_snap_alias(snapcraft_fn, snap_alias)

        if dry_run:
            click.echo("dry-run only:")
            click.echo(
                f"  > cd release/snap && bash build-scripts/docker-build {_snap}"
            )
        else:
            for line in sh.bash(
                "build-scripts/docker-build",
                _snap,
                _env=env,
                _cwd=str(build_path),
                _iter=True,
                _err_to_out=True,
            ):
                click.echo(line.strip())


def push(result_dir, dry_run):
    """ Promote to a snapstore channel/track

    Usage:

       ogc snap push --result-dir ./release/snap/build
    """
    # TODO: Verify channel is a ver/chan string
    #   re: [\d+\.]+\/(?:edge|stable|candidate|beta)
    for fname in glob.glob(f"{result_dir}/*.snap"):
        try:
            click.echo(f"Running: snapcraft push {fname}")
            if dry_run:
                click.echo("dry-run only:")
                click.echo(f"  > snapcraft push {fname}")
            else:
                for line in sh.snapcraft.push(fname, _iter=True, _err_to_out=True):
                    click.echo(line.strip())
        except sh.ErrorReturnCode_2 as e:
            click.echo("Failed to upload to snap store")
            click.echo(e.stdout)
            click.echo(e.stderr)
        except sh.ErrorReturnCode_1 as e:
            click.echo("Failed to upload to snap store")
            click.echo(e.stdout)
            click.echo(e.stderr)


def release(name, channel, version, dry_run):
    """ Release the most current revision snap to channel
    """
    latest_release = snapapi.latest(name, version)
    click.echo(latest_release)
    if dry_run:
        click.echo("dry-run only:")
        click.echo(f"  > snapcraft release {name} {latest_release['rev']} {channel}")
    else:
        click.echo(
            sh.snapcraft.release(name, latest_release["rev"], channel, _err_to_out=True)
        )
