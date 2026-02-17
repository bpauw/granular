# SPDX-License-Identifier: MIT

import uuid

type EntityId = str

UNSET_ENTITY_ID: EntityId = "00000000-0000-0000-0000-000000000000"


def generate_entity_id() -> EntityId:
    return str(uuid.uuid4())
