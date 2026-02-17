# SPDX-License-Identifier: MIT

from typing import NotRequired, Optional, TypedDict

import pendulum

from granular.model.entity_id import EntityId
from granular.model.filter import Filters


class Context(TypedDict):
    id: Optional[EntityId]
    name: Optional[str]
    active: Optional[bool]
    auto_added_tags: Optional[list[str]]
    auto_added_project: Optional[str]
    filter: Optional[Filters]
    default_note_folder: NotRequired[Optional[str]]
    created: pendulum.DateTime
    updated: pendulum.DateTime
