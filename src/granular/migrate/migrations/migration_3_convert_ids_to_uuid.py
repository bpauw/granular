# SPDX-License-Identifier: MIT

import uuid
from pathlib import Path
from typing import Any, Optional

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.migrate.registry import migration
from granular.model.entity_id import UNSET_ENTITY_ID
from granular.template.id_map import get_id_map_template

ENTITY_FILES: dict[str, tuple[str, str]] = {
    "tasks": ("DATA_TASKS_PATH", "tasks"),
    "time_audits": ("DATA_TIME_AUDIT_PATH", "time_audits"),
    "events": ("DATA_EVENTS_PATH", "events"),
    "timespans": ("DATA_TIMESPANS_PATH", "timespans"),
    "notes": ("DATA_NOTES_PATH", "notes"),
    "logs": ("DATA_LOGS_PATH", "logs"),
    "trackers": ("DATA_TRACKERS_PATH", "trackers"),
    "entries": ("DATA_ENTRIES_PATH", "entries"),
    "contexts": ("DATA_CONTEXT_PATH", "contexts"),
}


def _get_path(attr_name: str) -> Path:
    """Get a file path from the configuration module by attribute name."""
    return getattr(configuration, attr_name)


@migration(3)
def migrate() -> None:
    print("running migration 3: converting entity IDs from int to UUID...")

    # Step 1: Build ID mappings and update primary keys
    id_mappings = _build_and_apply_id_mappings()

    # Step 2: Update cross-entity foreign key references
    _update_foreign_key_references(id_mappings)

    # Step 3: Update external note frontmatter
    _update_external_note_frontmatter(id_mappings)

    # Step 4: Reset ephemeral data files
    _reset_ephemeral_data()

    # Step 5: Write migration report
    _write_migration_report(id_mappings)

    print("migration 3 complete!")


def _build_and_apply_id_mappings() -> dict[str, dict[int, str]]:
    """Build old_id -> new_uuid mappings for all entity types and update primary keys."""
    id_mappings: dict[str, dict[int, str]] = {}

    for entity_type, (path_attr, key) in ENTITY_FILES.items():
        file_path = _get_path(path_attr)
        if not file_path.exists():
            id_mappings[entity_type] = {}
            continue

        data = load(file_path.read_text(), Loader=Loader)
        if data is None:
            data = {key: []}

        mapping: dict[int, str] = {}
        entities = data.get(key, [])

        for entity in entities:
            old_id = entity.get("id")
            if old_id is not None:
                new_uuid = str(uuid.uuid4())
                mapping[old_id] = new_uuid
                entity["id"] = new_uuid

        # Remove next_id
        data.pop("next_id", None)

        # Save updated file
        file_path.write_text(dump(data, Dumper=Dumper))

        id_mappings[entity_type] = mapping

    return id_mappings


def _update_foreign_key_references(id_mappings: dict[str, dict[int, str]]) -> None:
    """Update all cross-entity foreign key references."""

    # Tasks: cloned_from_id -> tasks mapping, timespan_id -> timespans mapping
    _update_entity_fk(
        _get_path("DATA_TASKS_PATH"),
        "tasks",
        [
            ("cloned_from_id", id_mappings.get("tasks", {})),
            ("timespan_id", id_mappings.get("timespans", {})),
        ],
    )

    # Time audits: task_id -> tasks mapping
    _update_entity_fk(
        _get_path("DATA_TIME_AUDIT_PATH"),
        "time_audits",
        [("task_id", id_mappings.get("tasks", {}))],
    )

    # Entries: tracker_id -> trackers mapping
    # Special handling: tracker_id is non-optional, sentinel value 0 -> UNSET_ENTITY_ID
    _update_entry_tracker_fk(
        _get_path("DATA_ENTRIES_PATH"),
        id_mappings.get("trackers", {}),
    )

    # Notes: reference_id -> polymorphic lookup based on reference_type
    _update_polymorphic_fk(
        _get_path("DATA_NOTES_PATH"),
        "notes",
        "reference_id",
        "reference_type",
        {
            "task": id_mappings.get("tasks", {}),
            "time_audit": id_mappings.get("time_audits", {}),
            "event": id_mappings.get("events", {}),
            "timespan": id_mappings.get("timespans", {}),
        },
    )

    # Logs: reference_id -> polymorphic lookup based on reference_type
    _update_polymorphic_fk(
        _get_path("DATA_LOGS_PATH"),
        "logs",
        "reference_id",
        "reference_type",
        {
            "task": id_mappings.get("tasks", {}),
            "time_audit": id_mappings.get("time_audits", {}),
            "event": id_mappings.get("events", {}),
        },
    )


def _update_entity_fk(
    file_path: Path,
    key: str,
    fk_mappings: list[tuple[str, dict[int, str]]],
) -> None:
    """Update simple foreign key fields in an entity file."""
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        return

    for entity in data.get(key, []):
        for fk_field, mapping in fk_mappings:
            old_value = entity.get(fk_field)
            if old_value is not None and old_value in mapping:
                entity[fk_field] = mapping[old_value]
            elif old_value is not None and old_value not in mapping:
                print(
                    f"  WARNING: {key}.{fk_field} references non-existent ID {old_value}, setting to None"
                )
                entity[fk_field] = None

    file_path.write_text(dump(data, Dumper=Dumper))


def _update_entry_tracker_fk(
    file_path: Path,
    tracker_mapping: dict[int, str],
) -> None:
    """Update Entry.tracker_id with special handling for the sentinel value 0."""
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        return

    for entry in data.get("entries", []):
        tracker_id = entry.get("tracker_id")
        if tracker_id is None:
            # Should not happen (tracker_id is required), but handle gracefully
            entry["tracker_id"] = UNSET_ENTITY_ID
        elif tracker_id == 0:
            # Old sentinel value -> new sentinel
            entry["tracker_id"] = UNSET_ENTITY_ID
        elif tracker_id in tracker_mapping:
            entry["tracker_id"] = tracker_mapping[tracker_id]
        else:
            print(
                f"  WARNING: entries.tracker_id references non-existent tracker ID {tracker_id}, setting to UNSET"
            )
            entry["tracker_id"] = UNSET_ENTITY_ID

    file_path.write_text(dump(data, Dumper=Dumper))


def _update_polymorphic_fk(
    file_path: Path,
    key: str,
    fk_field: str,
    type_field: str,
    type_mappings: dict[str, dict[int, str]],
) -> None:
    """Update polymorphic foreign key fields based on a type discriminator."""
    if not file_path.exists():
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        return

    for entity in data.get(key, []):
        ref_id = entity.get(fk_field)
        ref_type = entity.get(type_field)

        if ref_id is None or ref_type is None:
            continue

        mapping = type_mappings.get(ref_type)
        if mapping is None:
            print(f"  WARNING: {key}.{type_field}={ref_type} has no mapping table")
            continue

        if ref_id in mapping:
            entity[fk_field] = mapping[ref_id]
        else:
            print(
                f"  WARNING: {key}.{fk_field} references non-existent {ref_type} ID {ref_id}, setting to None"
            )
            entity[fk_field] = None

    file_path.write_text(dump(data, Dumper=Dumper))


def _update_external_note_frontmatter(id_mappings: dict[str, dict[int, str]]) -> None:
    """Update frontmatter in external note markdown files."""
    notes_path = _get_path("DATA_NOTES_PATH")
    if not notes_path.exists():
        return

    notes_data = load(notes_path.read_text(), Loader=Loader)
    if notes_data is None:
        return

    # Load app config for note folder resolution
    config_path = configuration.APP_CONFIG_PATH
    config_data: Optional[dict[str, Any]] = None
    if config_path.exists():
        config_data = load(config_path.read_text(), Loader=Loader)

    for note in notes_data.get("notes", []):
        external_path = note.get("external_file_path")
        if external_path is None:
            continue

        # Resolve absolute path using note_folder_name
        note_folder_name = note.get("note_folder_name")
        abs_path = _resolve_note_file_path(external_path, note_folder_name, config_data)

        if abs_path is None or not abs_path.exists():
            folder_label = note_folder_name or "unknown"
            print(
                f"  WARNING: External note file not found: {folder_label}/{external_path}"
            )
            continue

        content = abs_path.read_text(encoding="utf-8")

        # Check if file has frontmatter
        if not content.startswith("---\n"):
            continue

        # Split frontmatter from content
        parts = content.split("---\n", maxsplit=2)
        if len(parts) < 3:
            continue

        frontmatter = load(parts[1], Loader=Loader)
        if frontmatter is None:
            continue

        body = parts[2]
        modified = False

        # Update id field
        if "id" in frontmatter:
            old_id = frontmatter["id"]
            if old_id in id_mappings.get("notes", {}):
                frontmatter["id"] = id_mappings["notes"][old_id]
                modified = True

        # Update reference_id field
        if "reference_id" in frontmatter and "reference_type" in frontmatter:
            ref_type = frontmatter["reference_type"]
            old_ref_id = frontmatter["reference_id"]

            type_to_mapping: dict[str, str] = {
                "task": "tasks",
                "time_audit": "time_audits",
                "event": "events",
                "timespan": "timespans",
            }

            mapping_key = type_to_mapping.get(ref_type)
            if mapping_key and old_ref_id in id_mappings.get(mapping_key, {}):
                frontmatter["reference_id"] = id_mappings[mapping_key][old_ref_id]
                modified = True

        if modified:
            new_content = "---\n" + dump(frontmatter, Dumper=Dumper) + "---\n" + body
            abs_path.write_text(new_content, encoding="utf-8")


def _resolve_note_file_path(
    relative_path: str,
    note_folder_name: Optional[str],
    config_data: Optional[dict[str, Any]],
) -> Optional[Path]:
    """Resolve the absolute path of an external note file."""
    if not note_folder_name or not config_data:
        return None

    note_folders = config_data.get("note_folders", [])
    if note_folders is None:
        note_folders = []

    folder_config = next(
        (f for f in note_folders if f["name"] == note_folder_name), None
    )

    if not folder_config:
        return None

    base_path = Path(folder_config["base_path"]).expanduser().resolve()
    return base_path / relative_path


def _reset_ephemeral_data() -> None:
    """Reset ephemeral data files that will be rebuilt on next use."""
    # Delete dispatch.yaml (will be recreated on next view)
    dispatch_path = _get_path("DATA_DISPATCH_PATH")
    if dispatch_path.exists():
        dispatch_path.unlink()

    # Reset id_map.yaml to empty (will be repopulated on next view)
    id_map_template = get_id_map_template()
    id_map_path = _get_path("DATA_ID_MAP_PATH")
    id_map_path.write_text(dump(id_map_template, Dumper=Dumper))


def _write_migration_report(id_mappings: dict[str, dict[int, str]]) -> None:
    """Write the ID migration map file for user reference."""
    report: dict[str, Any] = {}

    for entity_type, mapping in id_mappings.items():
        if mapping:
            report[entity_type] = {
                old_id: new_uuid for old_id, new_uuid in sorted(mapping.items())
            }

    report_path = configuration.DATA_PATH / "id_migration_map.yaml"

    header = (
        "# ID Migration Map: int -> UUID\n"
        "# Generated by migration 3 (convert IDs to UUIDs)\n"
        "# Use this file to update entity IDs in custom-views.yaml\n\n"
    )

    report_path.write_text(header + dump(report, Dumper=Dumper))
    print(f"  Migration report written to: {report_path}")
