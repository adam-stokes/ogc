""" Enums
"""


class SpecCore:
    META = "meta"
    PLAN = "plan"


SPEC_CORE_LIST = [SpecCore.META, SpecCore.PLAN]

SPEC_CORE_PLAN_PROPERTIES = (
    "env",
    "install",
    "before-script",
    "script",
    "after-script",
)


class ModuleMetadata:
    """ Provide enums for acceptable 'builtin' attributes as this is used when
    creating plugins for OGC ecosystem """

    # Plugin basics
    PLUGIN_NAME = "__plugin_name__"
    DESCRIPTION = "__description__"
    VERSION = "__version__"
    LICENSE = "__license__"

    # Plugin author and maintainers
    AUTHOR = "__author__"
    AUTHOR_EMAIL = "__author_email__"
    MAINTAINER = "__maintainer__"
    MAINTAINER_EMAIL = "__maintainer_email__"

    # Plugin CI status
    CI_STATUS = "__ci_status__"

    # Plugin Contributions
    GIT_REPO = "__git_repo__"
    GIT_REPO_ISSUES = "__git_repo_issues__"

    # Plugin Example Documentation
    EXAMPLE = "__example__"


MODULE_METADATA_MAPPING = [
    ModuleMetadata.PLUGIN_NAME,
    ModuleMetadata.DESCRIPTION,
    ModuleMetadata.VERSION,
    ModuleMetadata.LICENSE,
    ModuleMetadata.AUTHOR,
    ModuleMetadata.AUTHOR_EMAIL,
    ModuleMetadata.MAINTAINER,
    ModuleMetadata.MAINTAINER_EMAIL,
    ModuleMetadata.CI_STATUS,
    ModuleMetadata.GIT_REPO,
    ModuleMetadata.GIT_REPO_ISSUES,
    ModuleMetadata.EXAMPLE,
]
