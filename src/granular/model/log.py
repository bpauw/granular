# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict

import pendulum

from granular.model.entity_id import EntityId


class Log(TypedDict):
    id: Optional[EntityId]
    reference_id: Optional[EntityId]
    reference_type: Optional[str]
    timestamp: Optional[pendulum.DateTime]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
    tags: Optional[list[str]]
    project: Optional[str]
    text: Optional[str]
    color: Optional[str]
