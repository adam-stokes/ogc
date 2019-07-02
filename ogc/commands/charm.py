import click
from .base import cli
from .. import api


@click.group()
def charm():
    return


@click.command()
@click.option(
    "--layer-index",
    required=True,
    help="Charm layer index",
    default="https://charmed-kubernetes.github.io/layer-index/",
)
@click.option("--layer-list", required=True, help="list of layers in YAML format")
@click.option(
    "--layer-branch",
    required=True,
    help="Branch of layer to reference",
    default="master",
)
@click.option(
    "--retries", default=15, required=True, help="how many retries to perform"
)
@click.option(
    "--timeout", default=60, required=True, help="timeout between retries in seconds"
)
def pull_layers(layer_index, layer_list, layer_branch, retries, timeout):
    return api.charm.pull_layers(
        layer_index, layer_list, layer_branch, retries, timeout
    )


@click.command()
@click.option(
    "--charm-list", required=True, help="path to a file with list of charms in YAML"
)
@click.option("--layer-list", required=True, help="list of layers in YAML format")
@click.option("--layer-index", required=True, help="Charm layer index")
@click.option(
    "--charm-branch",
    required=True,
    help="Git branch to build charm from",
    default="master",
)
@click.option(
    "--layer-branch",
    required=True,
    help="Git branch to pull layers/interfaces from",
    default="master",
)
@click.option(
    "--resource-spec", required=True, help="YAML Spec of resource keys and filenames"
)
@click.option(
    "--filter-by-tag",
    required=True,
    help="only build for charms matching a tag, comma separate list",
    multiple=True,
)
@click.option(
    "--to-channel", required=True, help="channel to promote charm to", default="edge"
)
@click.option("--dry-run", is_flag=True)
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
    return api.charm.build(
        charm_list,
        layer_list,
        layer_index,
        charm_branch,
        layer_branch,
        resource_spec,
        filter_by_tag,
        to_channel,
        dry_run,
    )


@click.command()
@click.option("--bundle-list", required=True, help="list of bundles in YAML format")
@click.option(
    "--filter-by-tag",
    required=True,
    help="only build for charms matching a tag, comma separate list",
    multiple=True,
)
@click.option(
    "--bundle-repo",
    required=True,
    help="upstream repo for bundle builder",
    default="https://github.com/juju-solutions/bundle-canonical-kubernetes.git",
)
@click.option(
    "--to-channel", required=True, help="channel to promote charm to", default="edge"
)
@click.option("--dry-run", is_flag=True)
def build_bundles(bundle_list, filter_by_tag, bundle_repo, to_channel, dry_run):
    return api.charm.build_bundles(
        bundle_list, filter_by_tag, bundle_repo, to_channel, dry_run
    )


@click.command()
@click.option("--charm-list", required=True, help="path to charm list YAML")
@click.option(
    "--filter-by-tag",
    required=True,
    help="only build for charms matching a tag, comma separate list",
    multiple=True,
)
@click.option("--from-channel", required=True, help="Charm channel to publish from")
@click.option("--to-channel", required=True, help="Charm channel to publish to")
def promote(charm_list, filter_by_tag, from_channel, to_channel):
    return api.charm.promote(charm_list, filter_by_tag, from_channel, to_channel)


@click.command()
@click.option(
    "--charm-entity",
    required=True,
    help="Charmstore entity id (ie. cs~containers/flannel)",
)
@click.option(
    "--channel",
    required=True,
    default="unpublished",
    help="Charm channel to query entity",
)
@click.option("--builder", required=True, help="Path of resource builder")
@click.option(
    "--out-path", required=True, help="Temporary storage of built charm resources"
)
@click.option(
    "--resource-spec", required=True, help="YAML Spec of resource keys and filenames"
)
def resource(charm_entity, channel, builder, out_path, resource_spec):
    return api.charm.resource(charm_entity, channel, builder, out_path, resource_spec)


cli.add_command(charm)
charm.add_command(build)
charm.add_command(build_bundles)
charm.add_command(promote)
charm.add_command(pull_layers)
charm.add_command(resource)
