# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum


class TimeAudit(TypedDict):
    id: Optional[int]
    entity_type: str
    description: Optional[str]
    project: Optional[str]
    tags: Optional[list[str]]
    color: Optional[str]
    start: Optional[pendulum.DateTime]
    end: Optional[pendulum.DateTime]
    task_id: Optional[int]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
