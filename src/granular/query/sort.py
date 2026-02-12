# SPDX-License-Identifier: MIT

from copy import deepcopy
from typing import Any


def sort_items(
    items: list[dict[str, Any]], sort_instructions: list[str]
) -> list[dict[str, Any]]:
    sorted_items = deepcopy(items)

    for sort_instruction in reversed(sort_instructions):
        descending = False
        column = sort_instruction
        if " " in sort_instruction:
            direction, column = sort_instruction.split(" ")
            if direction == "desc":
                descending = True
        none_items = [item for item in sorted_items if item[column] is None]
        value_items = [item for item in sorted_items if item[column] is not None]
        value_items.sort(key=lambda item: item[column], reverse=descending)
        sorted_items = value_items + none_items

    return sorted_items
