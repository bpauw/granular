# SPDX-License-Identifier: MIT

from typing import Literal, Optional, TypedDict

import pendulum

EntryType = Literal["intra_day", "daily", "weekly", "monthly", "quarterly"]
ValueType = Literal["checkin", "quantitative", "multi_select", "pips"]


class Tracker(TypedDict):
    id: Optional[int]
    entity_type: str  # "tracker"
    name: str  # e.g., "Water intake"
    description: Optional[str]  # Optional longer description
    entry_type: EntryType  # Frequency constraint
    value_type: ValueType  # What kind of value to record

    # For quantitative trackers
    unit: Optional[str]  # e.g., "glasses", "mg", "km"

    # For multi_select trackers (option A: numeric range)
    scale_min: Optional[int]  # e.g., 1
    scale_max: Optional[int]  # e.g., 4

    # For multi_select trackers (option B: named options)
    options: Optional[list[str]]  # e.g., ["coffee", "tea", "water"]

    # Standard fields
    project: Optional[str]
    tags: Optional[list[str]]
    color: Optional[str]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    archived: Optional[pendulum.DateTime]  # Archived timestamp (not deleted)
    deleted: Optional[pendulum.DateTime]  # Soft delete
