from .. import charm


class ApplicationManifest:
    def __init__(self, application, manifest):
        self.application = application
        self.manifest = manifest

    @property
    def layers(self):
        return self.manifest["layers"]


class BundleData:
    def __init__(self, bundle, channel, namespace):
        self.bundle = bundle
        self.channel = channel
        self.namespace = namespace

    def __str__(self):
        return f"<{self.namespace}/self.channel/{self.bundle}>"

    def manifest(self, entity):
        return charm.get_manifest(entity["Charm"])

    @property
    def applications(self):
        """ Return applications in bundle
        """
        return [
            ApplicationManifest(app, self.manifest(entity))
            for app, entity in charm.get_bundle_applications(
                self.namespace, self.bundle, self.channel
            ).items()
        ]
