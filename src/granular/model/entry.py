# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict, Union

import pendulum


class Entry(TypedDict):
    id: Optional[int]
    entity_type: str  # "entry"
    tracker_id: int  # Reference to parent tracker
    timestamp: pendulum.DateTime  # When this entry was recorded

    # Value fields (only one is set based on tracker's value_type)
    # checkin: no value needed (presence = checked)
    # quantitative: numeric value
    # multi_select: selected option (int for scale, str for named options)
    value: Optional[Union[int, float, str]]

    # Standard fields
    project: Optional[str]  # Inherited from tracker
    tags: Optional[list[str]]  # Inherited from tracker
    color: Optional[str]  # Inherited from tracker
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]  # Soft delete
