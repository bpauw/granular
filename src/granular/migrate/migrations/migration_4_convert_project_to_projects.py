# SPDX-License-Identifier: MIT

from pathlib import Path

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.migrate.registry import migration

ENTITY_FILES: dict[str, tuple[str, str]] = {
    "tasks": ("DATA_TASKS_PATH", "tasks"),
    "time_audits": ("DATA_TIME_AUDIT_PATH", "time_audits"),
    "events": ("DATA_EVENTS_PATH", "events"),
    "timespans": ("DATA_TIMESPANS_PATH", "timespans"),
    "notes": ("DATA_NOTES_PATH", "notes"),
    "logs": ("DATA_LOGS_PATH", "logs"),
    "trackers": ("DATA_TRACKERS_PATH", "trackers"),
    "entries": ("DATA_ENTRIES_PATH", "entries"),
}


def _get_path(attr_name: str) -> Path:
    """Get a file path from the configuration module by attribute name."""
    return getattr(configuration, attr_name)


@migration(4)
def migrate() -> None:
    print("running migration 4: converting project to projects...")

    # Step 1: Convert entity files
    for entity_type, (path_attr, key) in ENTITY_FILES.items():
        _convert_entity_file(path_attr, key, entity_type)

    # Step 2: Convert contexts file
    _convert_contexts_file()

    # Step 3: Convert custom views file
    _convert_custom_views_file()

    print("migration 4 complete!")


def _convert_entity_file(path_attr: str, key: str, entity_type: str) -> None:
    """Convert project -> projects for all entities in a YAML file."""
    file_path = _get_path(path_attr)
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        data = {key: []}

    entities = data.get(key, [])
    converted_count = 0

    for entity in entities:
        if "project" in entity:
            old_value = entity.pop("project")
            if old_value is not None:
                entity["projects"] = [old_value]
            else:
                entity["projects"] = None
            converted_count += 1

    if converted_count > 0:
        file_path.write_text(dump(data, Dumper=Dumper))
        print(f"  {entity_type}: converted {converted_count} entities")


def _convert_contexts_file() -> None:
    """Convert auto_added_project -> auto_added_projects for all contexts."""
    file_path = _get_path("DATA_CONTEXT_PATH")
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        data = {"contexts": []}

    contexts = data.get("contexts", [])
    converted_count = 0

    for context in contexts:
        if "auto_added_project" in context:
            old_value = context.pop("auto_added_project")
            if old_value is not None:
                context["auto_added_projects"] = [old_value]
            else:
                context["auto_added_projects"] = None
            converted_count += 1

    if converted_count > 0:
        file_path.write_text(dump(data, Dumper=Dumper))
        print(f"  contexts: converted {converted_count} contexts")


def _convert_custom_views_file() -> None:
    """Convert project-related filters in custom views.

    Converts:
    - filter_type: str with property: project -> filter_type: project (remove property)
    - filter_type: str_regex with property: project -> filter_type: project_regex (remove property)
    """
    file_path = _get_path("DATA_CUSTOM_VIEWS_PATH")
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        return

    converted_count = 0

    # custom-views.yaml has a "views" key containing a list of view configs
    views = data.get("views", [])
    if views is None:
        views = []

    for view in views:
        converted_count += _convert_filters_in_view(view)

    if converted_count > 0:
        file_path.write_text(dump(data, Dumper=Dumper))
        print(f"  custom-views: converted {converted_count} filters")


def _convert_filters_in_view(view: dict) -> int:
    """Recursively convert project filters in a view's sub-views."""
    converted = 0

    # Check sub_views list
    sub_views = view.get("sub_views", [])
    if sub_views is None:
        sub_views = []

    for sub_view in sub_views:
        # Each sub_view may have a "filter" or "filters" field
        converted += _convert_filter_tree(sub_view.get("filter"))
        converted += _convert_filter_tree(sub_view.get("filters"))

    # Also check top-level filter
    converted += _convert_filter_tree(view.get("filter"))
    converted += _convert_filter_tree(view.get("filters"))

    return converted


def _convert_filter_tree(filter_node: dict | None) -> int:
    """Recursively convert project filters in a filter tree."""
    if filter_node is None:
        return 0

    converted = 0

    filter_type = filter_node.get("filter_type")
    prop = filter_node.get("property")

    # Convert str filter with property: project -> project filter
    if filter_type == "str" and prop == "project":
        filter_node["filter_type"] = "project"
        del filter_node["property"]
        converted += 1

    # Convert str_regex filter with property: project -> project_regex filter
    elif filter_type == "str_regex" and prop == "project":
        filter_node["filter_type"] = "project_regex"
        del filter_node["property"]
        converted += 1

    # Recurse into boolean combinators
    predicates = filter_node.get("predicates", [])
    if predicates:
        for pred in predicates:
            converted += _convert_filter_tree(pred)

    # Recurse into NOT predicate
    predicate = filter_node.get("predicate")
    if predicate:
        converted += _convert_filter_tree(predicate)

    return converted
