"""
snaps-source.py - Building snaps from source and promoting them to snapstore

"""
import click
from .base import cli


@click.group()
def snap():
    pass


@click.command()
@click.option("--snap-list", help="Path to supported snaps", required=True)
@click.option(
    "--starting-ver",
    help="Oldest k8s release to start from",
    required=True,
    default="1.13.7",
)
def sync_upstream(snap_list, starting_ver):
    return api.snap.sync_upstream(snap_list, starting_ver)


@click.command()
@click.option(
    "--repo-list",
    help="List of git repositories to create a new branches on",
    required=True,
)
@click.option(
    "--from-branch",
    help="Current git branch to checkout",
    required=True,
    default="master",
)
@click.option(
    "--to-branch",
    help="Git branch to create, this is typically upstream k8s version",
    required=True,
)
@click.option("--dry-run", is_flag=True)
def create_branches(repo_list, from_branch, to_branch, dry_run):
    return api.snap.create_branches(repo_list, from_branch, to_branch, dry_run)


@click.command()
@click.option("--repo", help="Git repository to create a new branch on", required=True)
@click.option(
    "--from-branch",
    help="Current git branch to checkout",
    required=True,
    default="master",
)
@click.option(
    "--to-branch",
    help="Git branch to create, this is typically upstream k8s version",
    required=True,
)
@click.option("--dry-run", is_flag=True)
def create_branch(repo, from_branch, to_branch, dry_run):
    return api.snap.create_branch(repo, from_branch, to_branch, dry_run)


@click.command()
@click.option("--snap", required=True, help="Snaps to build")
@click.option("--repo", help="Git repository for snap to build", required=True)
@click.option("--version", required=True, help="Version of k8s to build")
@click.option("--tag", required=True, help="Tag to build from")
@click.option(
    "--track",
    required=True,
    help="Snap track to release to, format as: `[<track>/]<risk>[/<branch>]`",
)
@click.option(
    "--owner",
    required=True,
    default="cdkbot",
    help="LP owner with access to managing the snap builds",
)
@click.option(
    "--snap-recipe-email", required=True, help="Snap store recipe authorized email"
)
@click.option(
    "--snap-recipe-password",
    required=True,
    help="Snap store recipe authorized user password",
)
@click.option(
    "--owner",
    required=True,
    default="cdkbot",
    help="LP owner with access to managing the snap builds",
)
@click.option("--dry-run", is_flag=True)
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
    return api.snap.create_snap_recipe(
        snap,
        version,
        track,
        owner,
        tag,
        repo,
        dry_run,
        snap_recipe_email,
        snap_recipe_password,
    )


@click.command()
@click.option("--snap", required=True, multiple=True, help="Snaps to build")
@click.option(
    "--build-path", required=True, default="release/snap", help="Path of snap builds"
)
@click.option("--version", required=True, help="Version of k8s to build")
@click.option(
    "--arch", required=True, default="amd64", help="Architecture to build against"
)
@click.option("--match-re", default="(?=\S*[-]*)([a-zA-Z-]+)(.*)", help="Regex matcher")
@click.option("--rename-re", help="Regex renamer, ie \1-eks")
@click.option("--dry-run", is_flag=True)
def build(snap, build_path, version, arch, match_re, rename_re, dry_run):
    return api.snap.build(snap, build_path, version, arch, match_re, rename_re, dry_run)


@click.command()
@click.option(
    "--result-dir",
    required=True,
    default="release/snap/build",
    help="Path of resulting snap builds",
)
@click.option("--dry-run", is_flag=True)
def push(result_dir, dry_run):
    return api.snap.push(result_dir, dry_run)


@click.command()
@click.option("--name", required=True, help="Snap name to release")
@click.option("--channel", required=True, help="Snapstore channel to release to")
@click.option("--version", required=True, help="Snap application version to release")
@click.option("--dry-run", is_flag=True)
def release(name, channel, version, dry_run):
    return api.snap.release(name, channel, version, dry_run)


cli.add_command(snap)
snap.add_command(create_snap_recipe)
snap.add_command(create_branch)
snap.add_command(sync_upstream)
snap.add_command(build)
snap.add_command(push)
snap.add_command(release)
