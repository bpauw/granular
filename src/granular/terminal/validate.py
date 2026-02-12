# SPDX-License-Identifier: MIT

import re
from typing import Optional

import typer

from granular.repository.context import ContextRepository


def validate_duration(duration: Optional[str]) -> Optional[str]:
    if duration is None:
        return None
    if not re.match(r"^([01]?\d|2[0-3]):([0-5]\d)$", duration):
        raise typer.BadParameter("Incorrect duration format")
    return duration


def validate_priority(priority: Optional[int]) -> Optional[int]:
    if priority is None:
        return None
    if not (1 <= priority <= 5):
        raise typer.BadParameter("Priority must be between 1 and 5 (inclusive)")
    return priority


def validate_unique_context_name(name: str, exclude_id: Optional[int] = None) -> str:
    """
    Validate that a context name is unique.

    Args:
        name: The context name to validate
        exclude_id: Optional context ID to exclude from the check (used when renaming)

    Raises:
        typer.BadParameter: If a context with this name already exists

    Returns:
        The validated name
    """
    repository = ContextRepository()
    all_contexts = repository.get_all_contexts()

    for context in all_contexts:
        if context["name"] == name and context["id"] != exclude_id:
            raise typer.BadParameter(f"A context with the name '{name}' already exists")

    return name
