""" Enums
"""

class SpecPhase:
    SETUP = 'setup'
    PLAN = 'plan'
    TEARDOWN = 'teardown'

# Please note this is the order in which the phases should execute
SPEC_PHASES = [SpecPhase.SETUP,
               SpecPhase.PLAN,
               SpecPhase.TEARDOWN]

class SpecCorePlugin:
    DOCS = 'docs'
    META = 'meta'

SPEC_CORE_PLUGINS = [SpecCorePlugin.DOCS,
                     SpecCorePlugin.META]


class ModuleMetadata:
    """ Provide enums for acceptable 'builtin' attributes as this is used when
    creating plugins for OGC ecosystem """

    # Plugin basics
    PLUGIN_NAME = '__plugin_name__'
    DESCRIPTION = '__description__'
    VERSION = '__version__'
    LICENSE = '__license__'

    # Plugin author and maintainers
    AUTHOR = '__author__'
    AUTHOR_EMAIL = '__author_email__'
    MAINTAINER = '__maintainer__'
    MAINTAINER_EMAIL = '__maintainer_email__'

    # Plugin CI status
    CI_STATUS = '__ci_status__'

    # Plugin Contributions
    GIT_REPO = '__git_repo__'
    GIT_REPO_ISSUES = '__git_repo_issues__'

    # Plugin Example Documentation
    EXAMPLE = '__example__'

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
