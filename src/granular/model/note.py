# SPDX-License-Identifier: MIT

from typing import NotRequired, Optional, TypedDict

import pendulum


class Note(TypedDict):
    id: Optional[int]
    reference_id: Optional[int]
    reference_type: Optional[str]
    timestamp: Optional[pendulum.DateTime]
    created: pendulum.DateTime
    updated: pendulum.DateTime
    deleted: Optional[pendulum.DateTime]
    tags: Optional[list[str]]
    project: Optional[str]
    text: Optional[str]
    color: Optional[str]
    external_file_path: NotRequired[Optional[str]]
    note_folder_name: NotRequired[Optional[str]]
    sync_frontmatter: NotRequired[Optional[bool]]
