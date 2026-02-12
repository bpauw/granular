# SPDX-License-Identifier: MIT

from typing import Literal, TypedDict

EntityType = Literal[
    "tasks",
    "time_audits",
    "events",
    "timespans",
    "notes",
    "logs",
    "trackers",
    "entries",
]


type IdMapDict = dict[EntityType, IdMapMapping]


class IdMap(TypedDict):
    """
    All dictionaries are mapped in the following way:

    Synthetic id : real entity id.

    This means that if you want to know the real id of an entity, and you have its synthetic id,
    then you index into the dictionary with the synthetic id.

    Example:

    Task with an id of 234.
    Synthetic id for that task is 7.

    real_task_id = id_map["tasks"][7] # returns 234
    """

    tasks: "IdMapMapping"
    time_audits: "IdMapMapping"
    events: "IdMapMapping"
    timespans: "IdMapMapping"
    notes: "IdMapMapping"
    logs: "IdMapMapping"
    trackers: "IdMapMapping"
    entries: "IdMapMapping"


class IdMapMapping(TypedDict):
    synthetic_to_real: dict[int, int]
    real_to_synthetic: dict[int, int]
