# SPDX-License-Identifier: MIT

from pathlib import Path

import pendulum
from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.migrate.registry import migration

# Map of entity type -> (old file path config attr, YAML wrapper key, new dir config attr)
ENTITY_CONVERSIONS: list[tuple[str, str, str, str]] = [
    ("tasks", "DATA_TASKS_PATH", "tasks", "DATA_TASKS_DIR"),
    ("events", "DATA_EVENTS_PATH", "events", "DATA_EVENTS_DIR"),
    ("time_audits", "DATA_TIME_AUDIT_PATH", "time_audits", "DATA_TIME_AUDIT_DIR"),
    ("timespans", "DATA_TIMESPANS_PATH", "timespans", "DATA_TIMESPANS_DIR"),
    ("notes", "DATA_NOTES_PATH", "notes", "DATA_NOTES_DIR"),
    ("logs", "DATA_LOGS_PATH", "logs", "DATA_LOGS_DIR"),
    ("trackers", "DATA_TRACKERS_PATH", "trackers", "DATA_TRACKERS_DIR"),
    ("entries", "DATA_ENTRIES_PATH", "entries", "DATA_ENTRIES_DIR"),
    ("contexts", "DATA_CONTEXT_PATH", "contexts", "DATA_CONTEXT_DIR"),
]


def _get_path(attr_name: str) -> Path:
    return getattr(configuration, attr_name)


@migration(6)
def migrate() -> None:
    print("running migration 6: converting entity files to individual files...")

    for entity_type, old_path_attr, yaml_key, new_dir_attr in ENTITY_CONVERSIONS:
        _convert_entity_type(entity_type, old_path_attr, yaml_key, new_dir_attr)

    _backfill_context_timestamps()

    print("migration 6 complete!")


def _convert_entity_type(
    entity_type: str,
    old_path_attr: str,
    yaml_key: str,
    new_dir_attr: str,
) -> None:
    old_file_path = _get_path(old_path_attr)
    new_dir_path = _get_path(new_dir_attr)

    # Create the directory (idempotent)
    new_dir_path.mkdir(parents=True, exist_ok=True)

    # Always create .gitkeep
    gitkeep_path = new_dir_path / ".gitkeep"
    if not gitkeep_path.exists():
        gitkeep_path.touch()

    # If old file doesn't exist or is empty, we're done
    if not old_file_path.exists():
        print(f"  {entity_type}: no existing file, created empty directory")
        return

    file_content = old_file_path.read_text()
    data = load(file_content, Loader=Loader)

    if data is None:
        print(f"  {entity_type}: file was empty, created empty directory")
        old_file_path.unlink()
        return

    entities = data.get(yaml_key, [])
    if not entities:
        print(f"  {entity_type}: no entities found, created empty directory")
        old_file_path.unlink()
        return

    # Write individual entity files
    for entity in entities:
        entity_id = entity.get("id")
        if entity_id is None:
            print(f"  WARNING: {entity_type} entity missing 'id', skipping")
            continue

        entity_file = new_dir_path / f"{entity_id}.yaml"
        entity_file.write_text(dump(entity, Dumper=Dumper))

    # Delete the old monolithic file
    old_file_path.unlink()

    print(f"  {entity_type}: converted {len(entities)} entities to individual files")


def _backfill_context_timestamps() -> None:
    """Ensure all context files have 'created' and 'updated' fields."""
    context_dir = _get_path("DATA_CONTEXT_DIR")
    if not context_dir.is_dir():
        return

    now_iso = pendulum.now("UTC").isoformat()
    backfilled = 0

    for file_path in context_dir.iterdir():
        if file_path.suffix != ".yaml" or file_path.name == ".gitkeep":
            continue

        context = load(file_path.read_text(), Loader=Loader)
        if context is None:
            continue

        modified = False
        if "created" not in context or context["created"] is None:
            context["created"] = now_iso
            modified = True
        if "updated" not in context or context["updated"] is None:
            context["updated"] = now_iso
            modified = True

        if modified:
            file_path.write_text(dump(context, Dumper=Dumper))
            backfilled += 1

    if backfilled > 0:
        print(
            f"  contexts: backfilled created/updated timestamps on {backfilled} entities"
        )
