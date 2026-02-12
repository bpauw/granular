# SPDX-License-Identifier: MIT

from typing import Optional

import pendulum

from granular.color import get_random_color
from granular.model.log import Log
from granular.repository.configuration import CONFIGURATION_REPO
from granular.repository.context import CONTEXT_REPO
from granular.template.log import get_log_template
from granular.time import now_utc, python_to_pendulum_utc_optional


def create_log_for_entity(
    text: str,
    reference_type: Optional[str],
    reference_id: Optional[int],
    entity_project: Optional[str],
    entity_tags: Optional[list[str]],
    timestamp: Optional[pendulum.DateTime] = None,
    add_tags: Optional[list[str]] = None,
    color: Optional[str] = None,
) -> Log:
    """
    Create a log entry for an entity (task, time_audit, or event).

    Handles merging tags from entity, context, and additional tags.
    Applies random color if configured and no explicit color provided.

    Args:
        text: Log text content
        reference_type: Type of entity (EntityType.TASK, etc.) or None for standalone log
        reference_id: ID of the referenced entity or None for standalone log
        entity_project: Project from the entity
        entity_tags: Tags from the entity
        timestamp: Optional timestamp (defaults to now)
        add_tags: Additional tags to add
        color: Explicit color (if None, may use random color)

    Returns:
        Log entry ready to be saved
    """
    active_context = CONTEXT_REPO.get_active_context()
    config = CONFIGURATION_REPO.get_config()

    # Start with entity tags
    log_tags = entity_tags if entity_tags is not None else []
    log_tags = list(log_tags)  # Make a copy

    # Add context tags if they're not already in the entity tags
    if active_context["auto_added_tags"] is not None:
        for tag in active_context["auto_added_tags"]:
            if tag not in log_tags:
                log_tags.append(tag)

    # Add any additional tags from the command
    if add_tags is not None:
        for tag in add_tags:
            if tag not in log_tags:
                log_tags.append(tag)

    # Set to None if empty
    final_tags = log_tags if len(log_tags) > 0 else None

    # Determine color: use provided color, or random if config enabled
    log_color = color
    if log_color is None and config["random_color_for_logs"]:
        log_color = get_random_color()

    # Create the log entry
    log_entry = get_log_template()
    log_entry["text"] = text
    log_entry["project"] = entity_project
    log_entry["tags"] = final_tags
    log_entry["color"] = log_color
    log_entry["timestamp"] = (
        python_to_pendulum_utc_optional(timestamp)
        if timestamp is not None
        else now_utc()
    )
    log_entry["reference_type"] = reference_type
    log_entry["reference_id"] = reference_id

    return log_entry
