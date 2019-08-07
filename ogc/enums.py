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

