# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum


class Event(TypedDict):
    id: Optional[int]
    entity_type: str
    title: Optional[str]
    description: Optional[str]
    location: Optional[str]
    project: Optional[str]
    tags: Optional[list[str]]
    color: Optional[str]
    start: pendulum.DateTime
    end: Optional[pendulum.DateTime]
    all_day: bool
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
    ical_source: Optional[str]
    ical_uid: Optional[str]
