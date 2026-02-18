# Changelog

## Version 0.5.0-alpha

### New

- Entities now support multiple projects — the `project` field has been replaced with `projects` (a list), bringing project handling fully in line with how tags work
- Added `--add-project` / `-ap` and `--remove-project` / `-rp` flags to all entity modify commands for granular project list management, plus `--remove-projects` / `-rpjs` to clear all projects
- Added `Project` and `ProjectRegex` filter types to the filter DSL for filtering entities by project list membership
- Added data migration (migration 4) that converts all existing `project` fields to `projects` lists across entity files, contexts, and custom view filters

### Updated

- The `--project` / `-p` flag on all add commands is now repeatable, allowing multiple projects at creation time (e.g., `gran task add "My task" -p proj1 -p proj2`)
- Context auto-added projects are now a list (`auto_added_projects`) and merge with explicitly provided projects instead of being overridden
- Project sync now indexes projects from all 8 entity types (previously only tasks, events, and time audits)
- All entity repositories now register new projects with the project index on save and modify (previously only tasks, events, and time audits did this)
- View commands display projects as comma-separated lists using the same formatting as tags
- The `--project` / `-p` filter on view commands now checks list membership instead of exact string equality
- Search now scans all projects in the list when `--search-in-project` is enabled

### Fixed

- Notes, logs, timespans, trackers, and entries now properly register projects with the project index (previously only tasks, events, and time audits did)

## Version 0.4.0-alpha

### New

- Added `EntityId` type alias system for centralized entity ID management (`model/entity_id.py`)
- Added data migration (migration 3) that converts all entity IDs from auto-incrementing integers to UUID v4 strings, preserving all cross-entity references
- Migration generates an `id_migration_map.yaml` report file mapping old integer IDs to new UUIDs, for use when manually updating `custom-views.yaml`

### Updated

- All entity IDs are now UUID v4 strings instead of sequential integers
- Removed `next_id` auto-increment counters from all YAML data files and repository code
- Updated all entity models, repositories, templates, services, and view/terminal layers to use the `EntityId` type
- The ID map system now maps synthetic integer IDs to UUID-based real IDs instead of integer-to-integer
- Entry template default `tracker_id` changed from `0` to a nil UUID sentinel (`UNSET_ENTITY_ID`)
- Initialization no longer writes `next_id` fields; default context uses a generated UUID

### Fixed

- Type annotations across the view and terminal layers now correctly reflect that real entity IDs are strings, not integers

## Version 0.3.0-alpha

### New

- Added `gran custom-view` (alias `gran cv`) top-level command group for user-defined compound views, separating them from the built-in `gran view` commands
- Added data migration to automatically rename `reports.yaml` to `custom-views.yaml` and update the YAML key for existing users

### Updated

- Custom views are now defined under the `custom_views` key in `custom-views.yaml` (previously `views` or `reports` key in `reports.yaml`)
- The `gran --help` output now lists `custom-view, cv` after `view, v` and includes the previously missing `version, ve` entry

## Version 0.2.0-alpha

### New

- Added `--start-date` / `-sd` option to the `cal-days` view command, allowing users to specify which date the multi-day calendar begins on instead of always starting from today
- The `cal-days` command now supports all the same date input formats as other calendar views (e.g., `YYYY-MM-DD`, `today`, `yesterday`, `tomorrow`, numeric day offsets)

### Updated

- The `cal-days` dispatch replay system now serializes and deserializes the start date for correct caching behavior
