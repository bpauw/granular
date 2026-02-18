# SPDX-License-Identifier: MIT

import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Optional, cast

import pendulum
import yaml.representer
from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration, time
from granular.model.context import Context
from granular.model.note import Note
from granular.repository.configuration import CONFIGURATION_REPO
from granular.repository.project import PROJECT_REPO
from granular.repository.tag import TAG_REPO
from granular.time import now_utc
from granular.model.entity_id import EntityId, generate_entity_id


class LiteralString(str):
    """String subclass to trigger literal block scalar style in YAML."""

    pass


def literal_string_representer(dumper: Any, data: str) -> Any:
    """YAML representer for literal block scalar (|) style."""
    # Convert to str to ensure compatibility with C dumper
    text = str(data)
    if "\n" in text:
        # Ensure text ends with newline to get | instead of |-
        if not text.endswith("\n"):
            text = text + "\n"
        return dumper.represent_scalar("tag:yaml.org,2002:str", text, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", text)


# Register the representer with the base representer class
yaml.representer.Representer.add_representer(LiteralString, literal_string_representer)
yaml.representer.SafeRepresenter.add_representer(
    LiteralString, literal_string_representer
)

# Also register with CDumper if available
try:
    from yaml.cyaml import CDumper as CYAMLDumper

    CYAMLDumper.add_representer(LiteralString, literal_string_representer)
except ImportError:
    pass


class NoteRepository:
    def __init__(self) -> None:
        self._notes: Optional[list[Note]] = None
        self.is_dirty = False

    @property
    def notes(self) -> list[Note]:
        if self._notes is None:
            self.__load_data()
        if self._notes is None:
            raise ValueError()
        return self._notes

    def __load_data(self) -> None:
        notes_data = load(configuration.DATA_NOTES_PATH.read_text(), Loader=Loader)
        raw_notes = notes_data["notes"]
        self._notes = [
            self.__convert_note_for_deserialization(note) for note in raw_notes
        ]

    def __save_data(self, notes: list[Note]) -> None:
        serializable_notes = [
            self.__convert_note_for_serialization(note) for note in deepcopy(notes)
        ]
        notes_data = {"notes": serializable_notes}
        configuration.DATA_NOTES_PATH.write_text(dump(notes_data, Dumper=Dumper))

    def flush(self) -> bool:
        if self._notes is not None and self.is_dirty:
            self.__save_data(self._notes)
            return True
        return False

    def __convert_note_for_serialization(self, note: Note) -> dict[str, Any]:
        serializable_note = cast(dict[str, Any], note)
        serializable_note["timestamp"] = time.datetime_to_iso_str_optional(
            serializable_note["timestamp"]
        )
        serializable_note["created"] = time.datetime_to_iso_str(
            serializable_note["created"]
        )
        serializable_note["updated"] = time.datetime_to_iso_str(
            serializable_note["updated"]
        )
        serializable_note["deleted"] = time.datetime_to_iso_str_optional(
            serializable_note["deleted"]
        )
        # Convert text field to LiteralString for block scalar formatting
        if serializable_note.get("text") is not None:
            serializable_note["text"] = LiteralString(serializable_note["text"])
        return serializable_note

    def __convert_note_for_deserialization(self, note: dict[str, Any]) -> Note:
        deserializable_note = note
        deserializable_note["timestamp"] = time.datetime_from_str_optional(
            deserializable_note["timestamp"]
        )
        deserializable_note["created"] = time.datetime_from_str(
            deserializable_note["created"]
        )
        deserializable_note["updated"] = time.datetime_from_str(
            deserializable_note["updated"]
        )
        deserializable_note["deleted"] = time.datetime_from_str_optional(
            deserializable_note["deleted"]
        )
        return cast(Note, deserializable_note)

    def _resolve_external_file_path(
        self, note: Note, config: configuration.Configuration
    ) -> Path:
        """
        Resolve absolute path from note_folder_name + external_file_path.

        Raises:
            ValueError: If folder name not found in config
        """
        folder_name = note.get("note_folder_name")
        relative_path = note.get("external_file_path")

        if not folder_name or not relative_path:
            raise ValueError("Note missing note_folder_name or external_file_path")

        # Type narrowing: after the check above, these are guaranteed to be str
        assert folder_name is not None
        assert relative_path is not None

        note_folders = config.get("note_folders", [])
        if note_folders is None:
            note_folders = []

        folder_config = next(
            (f for f in note_folders if f["name"] == folder_name), None
        )

        if not folder_config:
            available = [f["name"] for f in note_folders]
            raise ValueError(
                f"Note folder '{folder_name}' not found in config. "
                f"Available folders: {available}"
            )

        base_path = Path(folder_config["base_path"]).expanduser().resolve()
        return base_path / relative_path

    def _resolve_note_folder(
        self,
        config: configuration.Configuration,
        active_context: Context,
        folder_name_option: Optional[str],
    ) -> configuration.NoteFolderConfig:
        """
        Determine which folder config to use for external note.

        Priority:
        1. folder_name_option (CLI --folder)
        2. active_context default_note_folder
        3. Single configured folder
        4. Error

        Returns:
            NoteFolderConfig dict with 'name' and 'base_path'

        Raises:
            ValueError: If no folders configured or can't determine which to use
        """
        note_folders = config.get("note_folders", [])
        if note_folders is None:
            note_folders = []

        if len(note_folders) == 0:
            raise ValueError(
                "No note folders configured. "
                "Use: cous config note-folder add --name <name> --path <path>"
            )

        # Priority 1: Command-line option
        if folder_name_option:
            folder = next(
                (f for f in note_folders if f["name"] == folder_name_option), None
            )
            if not folder:
                available = [f["name"] for f in note_folders]
                raise ValueError(
                    f"Folder '{folder_name_option}' not found. Available: {available}"
                )
            return folder

        # Priority 2: Context default
        context_default = active_context.get("default_note_folder")
        if context_default:
            folder = next(
                (f for f in note_folders if f["name"] == context_default), None
            )
            if not folder:
                raise ValueError(
                    f"Context default folder '{context_default}' not found in config"
                )
            return folder

        # Priority 3: Single configured folder
        if len(note_folders) == 1:
            return note_folders[0]

        # No default and multiple folders
        available = [f["name"] for f in note_folders]
        raise ValueError(
            f"Multiple note folders configured: {available}. "
            f"Specify --folder or set default_note_folder in context."
        )

    def __sanitize_filename(self, name: str) -> str:
        """
        Sanitize user input for filename.

        Rules:
        - Remove invalid filename chars
        - Replace spaces with hyphens
        - Lowercase
        - Remove consecutive hyphens
        - Max 100 chars
        - Unicode allowed
        """
        # Remove invalid filename characters
        name = re.sub(r'[<>:"/\\|?*]', "", name)

        # Replace spaces with hyphens
        name = name.replace(" ", "-")

        # Remove multiple consecutive hyphens
        name = re.sub(r"-+", "-", name)

        # Strip leading/trailing hyphens
        name = name.strip("-")

        # Lowercase
        name = name.lower()

        # Limit length
        name = name[:100]

        # Fallback if empty
        if not name:
            name = "note"

        return name

    def __generate_filename(
        self, user_input: str, created_datetime: pendulum.DateTime, prefix_format: str
    ) -> str:
        """
        Generate filename from user input with timestamp prefix.

        Args:
            user_input: User-provided filename (without extension)
            created_datetime: DateTime for prefix
            prefix_format: Pendulum format string for timestamp

        Returns:
            Complete filename like "20241210-1430-meeting-notes.md"
        """
        # Generate timestamp prefix
        prefix = created_datetime.format(prefix_format)

        # Sanitize user input
        sanitized = self.__sanitize_filename(user_input)

        # Combine: prefix-name.md
        return f"{prefix}-{sanitized}.md"

    def __read_external_note_content(
        self, note: Note, config: configuration.Configuration
    ) -> str:
        """
        Read content from external markdown file.
        Strips frontmatter if present.

        Returns error message string if file or folder doesn't exist.
        """
        folder_name = note.get("note_folder_name") or ""
        relative_path = note.get("external_file_path") or ""

        try:
            absolute_path = self._resolve_external_file_path(note, config)
        except ValueError:
            # Folder not found in config
            return f"unable to find note file: {folder_name}/{relative_path}"

        if not absolute_path.exists():
            return f"unable to find note file: {folder_name}/{relative_path}"

        content = absolute_path.read_text(encoding="utf-8")

        # Strip frontmatter (between --- delimiters)
        if content.startswith("---\n"):
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                # Return content after second ---
                return parts[2]

        return content

    def __write_external_note_file(
        self,
        absolute_path: Path,
        content: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Write content to external markdown file.
        Optionally prepends YAML frontmatter.

        Args:
            absolute_path: Full path to file
            content: Markdown content
            metadata: Optional metadata dict for frontmatter
        """
        # Ensure directory exists
        absolute_path.parent.mkdir(parents=True, exist_ok=True)

        if metadata:
            # Generate frontmatter
            frontmatter = "---\n"
            frontmatter += dump(metadata, Dumper=Dumper)
            frontmatter += "---\n\n"
            full_content = frontmatter + content
        else:
            full_content = content

        absolute_path.write_text(full_content, encoding="utf-8")

    def __convert_note_metadata_for_serialization(self, note: Note) -> dict[str, Any]:
        """
        Convert note metadata to serializable dict for frontmatter.
        Excludes 'text', 'external_file_path', 'note_folder_name'.
        """
        metadata: dict[str, Any] = {
            "id": note["id"],
            "reference_id": note.get("reference_id"),
            "reference_type": note.get("reference_type"),
            "timestamp": time.datetime_to_iso_str_optional(note.get("timestamp")),
            "created": time.datetime_to_iso_str(note["created"]),
            "updated": time.datetime_to_iso_str(note["updated"]),
            "deleted": time.datetime_to_iso_str_optional(note.get("deleted")),
            "tags": note.get("tags"),
            "projects": note.get("projects"),
            "color": note.get("color"),
        }
        # Remove None values
        return {k: v for k, v in metadata.items() if v is not None}

    def __sync_external_note_frontmatter(
        self, note: Note, config: configuration.Configuration
    ) -> None:
        """
        Update frontmatter in external file without changing content.
        Only called when sync_frontmatter is enabled.
        """
        if not note.get("external_file_path"):
            return

        if not note.get("sync_frontmatter", False):
            return

        # Read current content (without frontmatter)
        content = self.__read_external_note_content(note, config)

        # Generate metadata dict
        metadata = self.__convert_note_metadata_for_serialization(note)

        # Resolve absolute path
        absolute_path = self._resolve_external_file_path(note, config)

        # Write back with updated frontmatter
        self.__write_external_note_file(absolute_path, content, metadata)

    def save_new_note(
        self,
        note: Note,
        external_filename: Optional[str] = None,
        note_folder_name: Optional[str] = None,
    ) -> EntityId:
        """
        Save new note. Handles both embedded and external notes.

        Args:
            note: Note to save
            external_filename: User-provided filename (for external notes)
            note_folder_name: Folder name (for external notes)

        Returns:
            Note ID
        """
        self.is_dirty = True

        note["id"] = generate_entity_id()

        # Deduplicate tags
        if note["tags"] is not None:
            note["tags"] = list(dict.fromkeys(note["tags"]))

        # Handle external note file creation
        if external_filename and note_folder_name:
            config = CONFIGURATION_REPO.get_config()

            # Get folder config
            note_folders = config.get("note_folders", [])
            if note_folders is None:
                note_folders = []

            folder_config = next(
                (f for f in note_folders if f["name"] == note_folder_name), None
            )
            if not folder_config:
                raise ValueError(f"Note folder '{note_folder_name}' not found")

            # Generate filename with timestamp prefix
            filename = self.__generate_filename(
                external_filename,
                note["created"],
                config.get("note_timestamp_prefix_format", "YYYYMMDD-HHmm"),
            )

            # Resolve base path
            base_path = Path(folder_config["base_path"]).expanduser().resolve()
            base_path.mkdir(parents=True, exist_ok=True)

            # Handle filename conflicts
            file_path = base_path / filename
            counter = 2
            while file_path.exists():
                name_without_ext = filename.rsplit(".", 1)[0]
                new_filename = f"{name_without_ext}-{counter}.md"
                file_path = base_path / new_filename
                counter += 1

            # Store RELATIVE path and folder name in note
            note["external_file_path"] = file_path.name
            note["note_folder_name"] = note_folder_name

            # Set sync_frontmatter
            if note.get("sync_frontmatter") is None:
                note["sync_frontmatter"] = config.get("sync_note_frontmatter", True)

            # Write external file with content
            content = note.get("text") or ""
            metadata = None
            if note.get("sync_frontmatter"):
                metadata = self.__convert_note_metadata_for_serialization(note)

            self.__write_external_note_file(file_path, content, metadata)

            # Clear text in notes.yaml (stored in file instead)
            note["text"] = None

        self.notes.append(note)

        # Update tag and project caches (additive only)
        if note["tags"] is not None:
            TAG_REPO.add_tags(note["tags"])
        if note["projects"] is not None:
            PROJECT_REPO.add_projects(note["projects"])

        return note["id"]

    def modify_note(
        self,
        id: EntityId,
        reference_id: Optional[EntityId],
        reference_type: Optional[str],
        timestamp: Optional[pendulum.DateTime],
        deleted: Optional[pendulum.DateTime],
        tags: Optional[list[str]],
        projects: Optional[list[str]],
        text: Optional[str],
        color: Optional[str],
        remove_reference_id: bool,
        remove_reference_type: bool,
        remove_timestamp: bool,
        remove_deleted: bool,
        remove_tags: bool,
        remove_projects: bool,
        remove_text: bool,
        remove_color: bool,
    ) -> None:
        self.is_dirty = True

        note = [note for note in self.notes if note["id"] == id][0]

        # Track if metadata changed (for frontmatter sync)
        metadata_changed = False

        # Apply modifications
        if reference_id is not None:
            note["reference_id"] = reference_id
            metadata_changed = True
        if reference_type is not None:
            note["reference_type"] = reference_type
            metadata_changed = True
        if timestamp is not None:
            note["timestamp"] = timestamp
            metadata_changed = True
        if deleted is not None:
            note["deleted"] = deleted
            metadata_changed = True
        if tags is not None:
            # Deduplicate tags
            deduplicated_tags = list(dict.fromkeys(tags))
            note["tags"] = deduplicated_tags
            TAG_REPO.add_tags(deduplicated_tags)
            metadata_changed = True
        if projects is not None:
            deduplicated_projects = list(dict.fromkeys(projects))
            note["projects"] = deduplicated_projects
            PROJECT_REPO.add_projects(deduplicated_projects)
            metadata_changed = True
        if color is not None:
            note["color"] = color
            metadata_changed = True

        # Handle text update
        if text is not None:
            if note.get("external_file_path"):
                # Update external file content
                config = CONFIGURATION_REPO.get_config()
                absolute_path = self._resolve_external_file_path(note, config)

                metadata = None
                if note.get("sync_frontmatter"):
                    metadata = self.__convert_note_metadata_for_serialization(note)

                self.__write_external_note_file(absolute_path, text, metadata)

                # Don't store text in notes.yaml
                note["text"] = None
            else:
                # Embedded note
                note["text"] = text

        # Handle removals
        if remove_reference_id:
            note["reference_id"] = None
            metadata_changed = True
        if remove_reference_type:
            note["reference_type"] = None
            metadata_changed = True
        if remove_timestamp:
            note["timestamp"] = None
            metadata_changed = True
        if remove_deleted:
            note["deleted"] = None
            metadata_changed = True
        if remove_tags:
            note["tags"] = None
            metadata_changed = True
        if remove_projects:
            note["projects"] = None
            metadata_changed = True
        if remove_text:
            if note.get("external_file_path"):
                # Update external file with empty content
                config = CONFIGURATION_REPO.get_config()
                absolute_path = self._resolve_external_file_path(note, config)

                metadata = None
                if note.get("sync_frontmatter"):
                    metadata = self.__convert_note_metadata_for_serialization(note)

                self.__write_external_note_file(absolute_path, "", metadata)
            note["text"] = None
        if remove_color:
            note["color"] = None
            metadata_changed = True

        # Always update 'updated' timestamp
        note["updated"] = now_utc()
        metadata_changed = True

        # Sync frontmatter if metadata changed and note is external
        if metadata_changed and note.get("external_file_path"):
            config = CONFIGURATION_REPO.get_config()
            self.__sync_external_note_frontmatter(note, config)

    def get_all_notes(self) -> list[Note]:
        """Get all notes. Loads content from external files where applicable."""

        notes = deepcopy(self.notes)
        config = CONFIGURATION_REPO.get_config()

        for note in notes:
            if note.get("external_file_path"):
                note["text"] = self.__read_external_note_content(note, config)

        return notes

    def get_note(self, id: EntityId) -> Note:
        """Get note by ID. Loads content from external file if applicable."""

        note = deepcopy([note for note in self.notes if note["id"] == id][0])

        # Load content from external file if needed
        if note.get("external_file_path"):
            config = CONFIGURATION_REPO.get_config()
            note["text"] = self.__read_external_note_content(note, config)

        return note


NOTE_REPO = NoteRepository()
