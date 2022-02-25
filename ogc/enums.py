""" Enums
"""


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
    ARCHES = "arches"
    PROVIDERS = "providers"


SPEC_CORE_LAYOUT_LIST = [
    SpecCoreLayout.RUNS_ON,
    SpecCoreLayout.USERNAME,
    SpecCoreLayout.SCRIPTS,
    SpecCoreLayout.ARCHES,
    SpecCoreLayout.PROVIDERS,
]
