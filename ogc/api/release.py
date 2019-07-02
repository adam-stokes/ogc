""" Tracks the progress of a release through it's different stages
"""


def get_phase(db, phase):
    """ checks for existing phase and returns result
    """
    print(db.get(phase, "fail"))


def set_phase(table, db, phase, result):
    """ sets a phase result

    0 for pass, 1 for fail, 2 for timeout
    """
    db[phase] = result
    table.put_item(Item=dict(db))
