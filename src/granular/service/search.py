# SPDX-License-Identifier: MIT

from typing import Optional, TypedDict, Union, cast

from granular.model.entity_id import EntityId
from granular.model.event import Event
from granular.model.log import Log
from granular.model.note import Note
from granular.model.task import Task
from granular.model.time_audit import TimeAudit
from granular.model.timespan import Timespan


class SearchResult(TypedDict):
    """Represents a unified search result across all entity types."""

    id: Optional[EntityId]
    entity_type: str
    projects: Optional[list[str]]
    description: Optional[str]
    tags: Optional[list[str]]


def __fuzzy_match(query: str, text: Optional[str]) -> bool:
    """
    Perform case-insensitive fuzzy matching.

    Fuzzy match means all characters from query must appear in text
    in the same order (but not necessarily consecutively).

    Args:
        query: The search query string
        text: The text to search within

    Returns:
        True if query fuzzy matches text, False otherwise
    """
    if text is None:
        return False

    query_lower = query.lower()
    text_lower = text.lower()

    # Simple substring match (case-insensitive)
    # For true fuzzy matching, you could implement subsequence matching
    # but substring is more intuitive for most users
    return query_lower in text_lower


def __convert_to_search_result(
    entity: Union[Task, TimeAudit, Event, Timespan, Note, Log],
    entity_type: str,
) -> SearchResult:
    """
    Convert any entity type to a SearchResult.

    Args:
        entity: The entity to convert
        entity_type: The type of the entity

    Returns:
        A SearchResult with normalized fields
    """
    # Determine the description field based on entity type
    description: Optional[str] = None
    if entity_type == "event":
        description = cast(Optional[str], entity.get("title"))
    elif entity_type in ("log", "note"):
        description = cast(Optional[str], entity.get("text"))
    else:
        description = cast(Optional[str], entity.get("description"))

    return SearchResult(
        id=entity.get("id"),
        entity_type=entity_type,
        projects=entity.get("projects"),
        description=description,
        tags=entity.get("tags"),
    )


def __search_in_entity(
    entity: Union[Task, TimeAudit, Event, Timespan, Note, Log],
    entity_type: str,
    query: str,
    search_in_description: bool,
    search_in_tags: bool,
    search_in_project: bool,
) -> bool:
    """
    Check if an entity matches the search query.

    Args:
        entity: The entity to search
        entity_type: The type of the entity
        query: The search query string
        search_in_description: Whether to search in description/title/text fields
        search_in_tags: Whether to search in tags
        search_in_project: Whether to search in project field

    Returns:
        True if entity matches query, False otherwise
    """
    matched = False

    # Search in description field (or title for events, text for notes/logs)
    if search_in_description:
        description_field: Optional[str] = None

        if entity_type == "event":
            description_field = cast(Optional[str], entity.get("title"))
        elif entity_type in ("log", "note"):
            description_field = cast(Optional[str], entity.get("text"))
        else:
            description_field = cast(Optional[str], entity.get("description"))

        if __fuzzy_match(query, description_field):
            matched = True

    # Search in tags
    if search_in_tags and not matched:
        tags = entity.get("tags")
        if tags is not None:
            for tag in tags:
                if __fuzzy_match(query, tag):
                    matched = True
                    break

    # Search in projects
    if search_in_project and not matched:
        projects = entity.get("projects")
        if projects is not None:
            for project in projects:
                if __fuzzy_match(query, project):
                    matched = True
                    break

    return matched


def search_entities(
    query: str,
    tasks: list[Task] = [],
    time_audits: list[TimeAudit] = [],
    events: list[Event] = [],
    timespans: list[Timespan] = [],
    notes: list[Note] = [],
    logs: list[Log] = [],
    search_in_description: bool = True,
    search_in_tags: bool = False,
    search_in_project: bool = False,
) -> list[SearchResult]:
    """
    Search across multiple entity types with fuzzy matching.

    Args:
        query: The search query string
        tasks: List of tasks to search
        time_audits: List of time audits to search
        events: List of events to search
        timespans: List of timespans to search
        notes: List of notes to search
        logs: List of logs to search
        search_in_description: Whether to search in description/title/text fields
        search_in_tags: Whether to search in tags
        search_in_project: Whether to search in project field

    Returns:
        List of SearchResult objects matching the query
    """
    results: list[SearchResult] = []

    # Search tasks
    for task in tasks:
        if __search_in_entity(
            task,
            "task",
            query,
            search_in_description,
            search_in_tags,
            search_in_project,
        ):
            results.append(__convert_to_search_result(task, "task"))

    # Search time audits
    for time_audit in time_audits:
        if __search_in_entity(
            time_audit,
            "time_audit",
            query,
            search_in_description,
            search_in_tags,
            search_in_project,
        ):
            results.append(__convert_to_search_result(time_audit, "time_audit"))

    # Search events
    for event in events:
        if __search_in_entity(
            event,
            "event",
            query,
            search_in_description,
            search_in_tags,
            search_in_project,
        ):
            results.append(__convert_to_search_result(event, "event"))

    # Search timespans
    for timespan in timespans:
        if __search_in_entity(
            timespan,
            "timespan",
            query,
            search_in_description,
            search_in_tags,
            search_in_project,
        ):
            results.append(__convert_to_search_result(timespan, "timespan"))

    # Search notes
    for note in notes:
        if __search_in_entity(
            note,
            "note",
            query,
            search_in_description,
            search_in_tags,
            search_in_project,
        ):
            results.append(__convert_to_search_result(note, "note"))

    # Search logs
    for log in logs:
        if __search_in_entity(
            log, "log", query, search_in_description, search_in_tags, search_in_project
        ):
            results.append(__convert_to_search_result(log, "log"))

    return results
