# Granular

Life management in the terminal.

> **Alpha Software** — Granular is under active development. It contains bugs and there are planned breaking changes to the data format. Use with caution.

> **Contributing** — Please note that this software is currently closed to anonymous outside code contributions.

Granular is a CLI application for managing tasks, time tracking, events, timespans, notes, logs, and habit tracking — all from the terminal. Data is stored as plain YAML files on disk with optional git versioning for full change history.

**Documentation:** https://granular.sh

---

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Entity Types](#entity-types)
  - [Contexts](#contexts)
  - [Synthetic IDs](#synthetic-ids)
  - [Soft Deletion](#soft-deletion)
- [Commands](#commands)
  - [Tasks](#tasks)
  - [Time Audits](#time-audits)
  - [Events](#events)
  - [Timespans](#timespans)
  - [Notes](#notes)
  - [Logs](#logs)
  - [Trackers](#trackers)
  - [Contexts](#contexts-commands)
  - [Views](#views)
  - [Custom Views Command](#custom-views-command)
  - [Search](#search)
  - [Configuration](#configuration-commands)
- [Views Reference](#views-reference)
  - [List Views](#list-views)
  - [Detail Views](#detail-views)
  - [Calendar Views](#calendar-views)
  - [Agenda](#agenda)
  - [Gantt Chart](#gantt-chart)
  - [Story View](#story-view)
  - [Heatmaps](#heatmaps)
  - [Tracker Views](#tracker-views)
- [Custom Views](#custom-views)
  - [Defining Custom Views](#defining-custom-views)
  - [Sub-View Types](#sub-view-types)
- [Filter DSL](#filter-dsl)
  - [Boolean Filters](#boolean-filters)
  - [Property Filters](#property-filters)
  - [Tag Filters](#tag-filters)
- [Date and Time Input](#date-and-time-input)
- [ID Ranges](#id-ranges)
- [Configuration](#configuration)
  - [Configuration Options](#configuration-options)
  - [External Notes](#external-notes)
  - [iCal Sync](#ical-sync)
  - [Git Versioning](#git-versioning)
- [Command Aliases](#command-aliases)
- [Data Storage](#data-storage)
- [Acknowledgements](#acknowledgements)

---

## Installation

Requires **Python 3.14**.

Clone this repo.

Install with [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended):

```sh
uv tool install . --reinstall
```

The CLI is invoked with the `gran` command.

---

## Quick Start

```sh
# Add your first task
gran task add "Buy groceries" --tag shopping --due tomorrow

# Add another task with a project and priority
gran task add "Write report" --project work.reports --priority 2 --scheduled today

# Start tracking time on a task
gran task track 1

# Stop the active time audit
gran audit stop

# View your tasks
gran view tasks

# View today's agenda
gran view agenda

# View a 7-day calendar
gran view cal-week

# Add a note to a task
gran task note 1

# Search across all entities
gran search "groceries"

# Mark a task as complete
gran task complete 1
```

---

## Core Concepts

### Entity Types

Granular manages eight types of entities:

| Entity | Description |
|---|---|
| **Task** | A discrete unit of work with optional scheduling, due dates, priority, and time estimates |
| **Time Audit** | A time tracking record with start/end timestamps, optionally linked to a task |
| **Event** | A calendar event with start/end times, location, and optional iCal sync |
| **Timespan** | A longer-duration period (e.g., a project phase, a trip, a sprint) |
| **Note** | Free-form text, either inline or stored as an external markdown file. Can be linked to other entities |
| **Log** | A timestamped journal entry. Can be linked to other entities |
| **Tracker** | A habit or metric tracker with configurable frequency and value types |
| **Entry** | A single data point recorded against a tracker |

All entities support **projects** (hierarchical, dot-separated: `work.reports`), **tags**, and **colors**.

### Contexts

Contexts are named work environments that change how Granular behaves:

- **Auto-added tags** — Tags automatically applied to new entities created in the context
- **Auto-added project** — A project automatically set on new entities
- **Filters** — A filter automatically applied to all views, so you only see relevant data
- **Default note folder** — Where external notes are saved by default

A `default` context is created on first run. Activate a context with:

```sh
gran context activate work
```

### Synthetic IDs

When viewing entities, Granular displays short sequential IDs (1, 2, 3...) rather than internal database IDs. These synthetic IDs are mapped to real IDs behind the scenes. This keeps the IDs you type short and predictable. The mapping resets on each view command by default (configurable via `clear_ids_on_view`).

### Soft Deletion

All delete operations are soft deletes — they set a `deleted` timestamp rather than removing data. Use `--include-deleted` / `-i` on view commands to see deleted entities. Undo a delete by modifying the entity with `--remove-deleted`.

---

## Commands

Every command group and subcommand has a short alias. For example, `gran task add` can be written as `gran t a`. See [Command Aliases](#command-aliases) for the full list.

All modify commands accept [ID ranges](#id-ranges) to operate on multiple entities at once (e.g., `1,3-5`).

### Tasks

```sh
gran task add <description> [options]    # Create a task
gran task modify <id> [options]          # Modify a task
gran task complete <id>                  # Mark as completed
gran task not-complete <id>              # Mark as not completed
gran task cancel <id>                    # Mark as cancelled
gran task delete <id>                    # Soft delete
gran task clone <id> [options]           # Clone a task
gran task track <id>                     # Start time tracking from a task
gran task log <task_id>                  # Add a log entry (opens editor)
gran task note <task_id>                 # Add a note (opens editor)
gran task color                          # Assign random colors to uncolored tasks
```

**Task add options:**

| Option | Short | Description |
|---|---|---|
| `--project` | `-p` | Project name (e.g., `work.reports`) |
| `--tag` | `-t` | Tag (repeatable for multiple tags) |
| `--priority` | `-pr` | Priority 1-5 (1 = highest) |
| `--estimate` | `-e` | Time estimate in `HH:mm` format |
| `--scheduled` | `-s` | Scheduled date |
| `--due` | `-u` | Due date |
| `--started` | `-a` | Started date |
| `--color` | `-col` | Display color |
| `--timespan-id` | `-ts` | Link to a timespan |

**Task modify** supports all of the above plus `--remove-*` variants to clear fields (e.g., `--remove-project`, `--remove-due`), `--add-tag`/`--remove-tag` for tag management, and `--completed`/`--not-completed`/`--cancelled`/`--deleted` to set status timestamps directly.

### Time Audits

```sh
gran audit add <description> [options]   # Start a time audit (auto-stops any active one)
gran audit modify <id> [options]         # Modify a time audit
gran audit stop                          # Stop the active time audit
gran audit delete <id>                   # Soft delete
gran audit move-adjacent-start <id> -s <datetime>  # Move start and adjust previous audit's end
gran audit move-adjacent-end <id> -e <datetime>    # Move end and adjust next audit's start
gran audit log <time_audit_id>           # Add a log entry (opens editor)
gran audit note <time_audit_id>          # Add a note (opens editor)
gran audit color                         # Assign random colors to uncolored audits
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--project` | `-p` | Project name |
| `--tag` | `-t` | Tag (repeatable) |
| `--color` | `-col` | Display color |
| `--start` | `-s` | Start time (defaults to now) |
| `--end` | `-e` | End time (omit to leave running) |
| `--task-id` | `-tid` | Link to a task |

### Events

```sh
gran event add <title> [options]         # Create an event
gran event modify <id> [options]         # Modify an event
gran event delete <id>                   # Soft delete
gran event sync-ics                      # Sync events from configured iCal sources
gran event hard-delete-ics-events        # Permanently delete all synced iCal events
gran event log <event_id>               # Add a log entry
gran event note <event_id>              # Add a note
gran event color                         # Assign random colors
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--description` | `-d` | Event description |
| `--location` | `-l` | Event location |
| `--project` | `-p` | Project name |
| `--tag` | `-t` | Tag (repeatable) |
| `--color` | `-col` | Display color |
| `--start` | `-s` | Start time |
| `--end` | `-e` | End time |
| `--all-day` | `-a` | Mark as all-day event |

### Timespans

```sh
gran timespan add <description> [options]   # Create a timespan
gran timespan modify <id> [options]         # Modify a timespan
gran timespan complete <id>                 # Mark as completed
gran timespan delete <id>                   # Soft delete
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--project` | `-p` | Project name |
| `--tag` | `-t` | Tag (repeatable) |
| `--color` | `-col` | Display color |
| `--start` | `-s` | Start date |
| `--end` | `-e` | End date |

### Notes

Notes open your `$EDITOR` (defaults to `nano`) for text input.

```sh
gran note add [options]                  # Create a standalone note
gran note modify <id> [options]          # Modify a note
gran note delete <id>                    # Soft delete
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--project` | `-p` | Project name |
| `--tag` | `-t` | Tag (repeatable) |
| `--timestamp` | `-ts` | Timestamp for ordering |
| `--color` | `-c` | Display color |
| `--ref-task` | `-rt` | Link to a task |
| `--ref-time-audit` | `-rta` | Link to a time audit |
| `--ref-event` | `-re` | Link to an event |
| `--ref-timespan` | `-rts` | Link to a timespan |
| `--external` | `-x` | Store as an external markdown file |
| `--folder` | `-f` | Note folder name (must be configured) |

Only one reference can be set at a time. Notes can also be created directly from other entities (e.g., `gran task note 1`).

### Logs

Logs open your `$EDITOR` for text input.

```sh
gran log add [options]                   # Create a standalone log
gran log modify <id> [options]           # Modify a log
gran log delete <id>                     # Soft delete
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--project` | `-p` | Project name |
| `--tag` | `-t` | Tag (repeatable) |
| `--color` | `-col` | Display color |
| `--timestamp` | `-ts` | Timestamp |
| `--ref-task` | `-rt` | Link to a task |
| `--ref-time-audit` | `-rta` | Link to a time audit |
| `--ref-event` | `-re` | Link to an event |

### Trackers

Trackers support configurable frequency and value types for habit tracking and metric recording.

```sh
gran tracker add <name> [options]        # Create a tracker
gran tracker modify <id> [options]       # Modify a tracker
gran tracker delete <id>                 # Soft delete
gran tracker archive <id>               # Archive (hide from active views)
gran tracker unarchive <id>             # Unarchive
gran tracker entry <tracker_id> [options]          # Record an entry
gran tracker entry-modify <id> [options]           # Modify an entry
gran tracker entry-delete <entry_id>               # Delete an entry
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--type` | `-t` | Frequency: `intra_day`, `daily`, `weekly`, `monthly`, `quarterly` (default: `daily`) |
| `--value` | `-v` | Value type: `checkin`, `quantitative`, `multi_select`, `pips` (default: `checkin`) |
| `--unit` | `-u` | Unit for quantitative trackers (e.g., `glasses`, `km`) |
| `--scale-min` | | Minimum value for numeric multi_select |
| `--scale-max` | | Maximum value for numeric multi_select |
| `--option` | `-o` | Named option for multi_select (repeatable) |
| `--description` | `-d` | Tracker description |
| `--project` | `-p` | Project name |
| `--tag` | `-tg` | Tag (repeatable) |
| `--color` | `-col` | Display color |

**Entry options:**

| Option | Short | Description |
|---|---|---|
| `--value` | `-v` | Value (for quantitative, multi_select, or pips trackers) |
| `--timestamp` | `-ts` | Time of entry (default: now) |
| `--date` | `-d` | Date of entry (default: today) |
| `--add-tag` | `-at` | Additional tags |

### Contexts Commands

```sh
gran context add <name> [options]        # Create a context
gran context activate <name>             # Activate a context
```

**Add options:**

| Option | Short | Description |
|---|---|---|
| `--auto-added-tag` | `-a` | Tags auto-applied to new entities (repeatable) |
| `--auto-added-project` | `-p` | Project auto-set on new entities |
| `--default-note-folder` | `-dnf` | Default folder for external notes |

### Views

The `gran view` command group contains all built-in views. See [Views Reference](#views-reference) for detailed documentation.

```sh
gran view tasks        # Task list
gran view task <id>    # Single task detail
gran view agenda       # Agenda view
gran view cal-day      # Day calendar
gran view gantt        # Gantt chart
# ... and many more
```

### Custom Views Command

User-defined compound views have their own dedicated command group: `gran custom-view` (alias: `gran cv`). This keeps custom views separate from the built-in view commands.

Any custom views defined in your `custom-views.yaml` data file are registered as subcommands under this group. For example, if you define a custom view named `dashboard`, you invoke it with:

```sh
gran custom-view dashboard
# or using the alias:
gran cv dashboard
```

Run `gran custom-view --help` (or `gran cv --help`) to see all available custom views.

See [Custom Views](#custom-views) for details on how to define custom views in YAML.

### Search

Search across all entity types:

```sh
gran search <query> [options]
```

| Option | Short | Description |
|---|---|---|
| `--search-in-description` | `-d` | Search in description/title/text (default: on) |
| `--search-in-tags` | `-t` | Search in tags |
| `--search-in-project` | `-p` | Search in project field |
| `--tasks/--no-tasks` | | Include/exclude tasks (default: on) |
| `--time-audits/--no-time-audits` | | Include/exclude time audits (default: on) |
| `--events/--no-events` | | Include/exclude events (default: on) |
| `--timespans/--no-timespans` | | Include/exclude timespans (default: on) |
| `--notes/--no-notes` | | Include/exclude notes (default: on) |
| `--logs/--no-logs` | | Include/exclude logs (default: on) |
| `--include-deleted` | `-i` | Include deleted entities |
| `--no-wrap` | | Disable text wrapping |

### Configuration Commands

```sh
gran config view                         # Display current configuration
gran config set [options]                # Update configuration

# Note folder management
gran config note-folder add --name <name> --path <path>
gran config note-folder list
gran config note-folder remove <name>
gran config note-folder modify <name> [--new-name] [--new-path]

# Maintenance
gran config resync-projects-and-tags     # Rebuild project and tag indexes
```

---

## Views Reference

All view commands are under `gran view` (alias: `gran v`). Most list views support these common filtering options:

| Option | Short | Description |
|---|---|---|
| `--include-deleted` | `-i` | Show soft-deleted entities |
| `--tag` | `-t` | Filter by tag (all must match, repeatable) |
| `--tag-regex` | `-tr` | Filter by tag regex (repeatable) |
| `--no-tag` | `-nt` | Exclude entities with these tags (repeatable) |
| `--no-tag-regex` | `-ntr` | Exclude entities with tags matching regex |
| `--project` | `-p` | Filter by project |
| `--no-color` | | Disable entity color in rows |
| `--no-wrap` | | Disable text wrapping |

### List Views

| Command | Alias | Description |
|---|---|---|
| `gran view tasks` | `gran v ts` | All tasks in a table |
| `gran view time-audits` | `gran v tas` | All time audits in a table |
| `gran view events` | `gran v es` | All events in a table |
| `gran view timespans` | `gran v ts` | All timespans in a table |
| `gran view notes` | `gran v ns` | All notes in a table |
| `gran view logs` | `gran v ls` | All logs in a table |
| `gran view trackers` | `gran v trs` | All trackers |
| `gran view entries <tracker_id>` | `gran v ens` | Entries for a tracker |
| `gran view contexts` | `gran v cx` | All contexts |
| `gran view projects` | `gran v p` | All unique projects |
| `gran view tags` | `gran v tg` | All unique tags |

**Tasks** has additional options: `--scheduled`/`-s`, `--due`/`-d` for date filtering, and `--column`/`-c` to select specific columns.

**Logs and Notes** have additional options: `--reference-type`/`-rt` and `--reference-id`/`-rid` to filter by parent entity.

### Detail Views

| Command | Alias | Description |
|---|---|---|
| `gran view task <id>` | `gran v t` | Full detail for a single task |
| `gran view time-audit <id>` | `gran v ta` | Full detail for a single time audit |
| `gran view time-audit-active` | `gran v taa` | Currently active time audit |
| `gran view event <id>` | `gran v e` | Full detail for a single event |
| `gran view timespan <id>` | `gran v tsp` | Full detail for a single timespan |
| `gran view note <id>` | `gran v n` | Full detail for a single note |
| `gran view log <id>` | `gran v l` | Full detail for a single log |
| `gran view tracker <id>` | `gran v tr` | Full detail for a single tracker |
| `gran view context-current-name` | `gran v ccn` | Name of the active context |

### Calendar Views

| Command | Alias | Description |
|---|---|---|
| `gran view cal-day` | `gran v cd` | Single day calendar |
| `gran view cal-week` | `gran v cw` | Multi-day horizontal calendar |
| `gran view cal-days` | `gran v cds` | Multi-day calendar (defaults to starting from today) |
| `gran view cal-month` | `gran v cm` | Monthly calendar grid |
| `gran view cal-quarter` | `gran v cq` | Quarterly calendar (3 months) |

**Common calendar options:**

| Option | Short | Description |
|---|---|---|
| `--date` | `-d` | Date to display (day/month views) |
| `--granularity` | `-g` | Time slot interval in minutes: `15`, `30`, or `60` (default: `60`) |
| `--start` | `-s` | Start time filter (`HH:mm`) |
| `--end` | `-e` | End time filter (`HH:mm`) |
| `--show-scheduled-tasks/--no-show-scheduled-tasks` | | Show scheduled tasks (default: on) |
| `--show-due-tasks/--no-show-due-tasks` | | Show due tasks (default: on) |
| `--show-time-audits/--no-show-time-audits` | | Show time audits (default: on) |
| `--show-trackers/--no-show-trackers` | | Show tracker entries (default: off) |

Week and multi-day views (`cal-week`, `cal-days`) also support:

| Option | Short | Description |
|---|---|---|
| `--start-date` | `-sd` | Start date for the calendar (defaults to start of current week for `cal-week`, today for `cal-days`). Accepts the same [date input formats](#date-and-time-input): `YYYY-MM-DD`, `today`, `yesterday`, `tomorrow`, or a numeric day offset like `1` or `-3` |
| `--num-days` | `-n` | Number of days to display (default: 7) |
| `--day-width` | `-w` | Width of each day column in characters (default: 30) |

**Examples:**

```sh
# Show a 7-day calendar starting from today (default)
gran view cal-days

# Show a 7-day calendar starting from a specific date
gran view cal-days --start-date 2026-01-01

# Show 14 days starting from 3 days ago
gran view cal-days -sd -3 --num-days 14

# Show a week starting from a specific date
gran view cal-week --start-date 2026-03-01
```

### Agenda

A day-by-day agenda view showing upcoming items:

```sh
gran view agenda [options]
```

| Option | Short | Description |
|---|---|---|
| `--num-days` | `-n` | Number of days to show (default: 7) |
| `--start` | `-s` | Start date |
| `--only-active-days/--all-days` | | Only show days with activity |
| `--show-scheduled-tasks/--no-show-scheduled-tasks` | | Default: on |
| `--show-due-tasks/--no-show-due-tasks` | | Default: on |
| `--show-events/--no-show-events` | | Default: on |
| `--show-timespans/--no-show-timespans` | | Default: on |
| `--show-time-audits/--no-show-time-audits` | | Default: off |
| `--show-logs/--no-show-logs` | | Default: off |
| `--show-notes/--no-show-notes` | | Default: off |
| `--limit-note-lines` | | Max lines per note |
| `--project` | `-p` | Filter by project |

### Gantt Chart

A timeline view for timespans, events, and optionally tasks and trackers:

```sh
gran view gantt [options]
```

| Option | Short | Description |
|---|---|---|
| `--start` | `-s` | Timeline start date |
| `--end` | `-e` | Timeline end date |
| `--granularity` | `-g` | `day`, `week`, or `month` (default: `day`) |
| `--show-tasks/--no-show-tasks` | | Default: off |
| `--show-timespans/--no-show-timespans` | | Default: on |
| `--show-events/--no-show-events` | | Default: on |
| `--show-trackers/--no-show-trackers` | | Default: off |
| `--left-width` | `-lw` | Width of the label column (default: 40) |

### Story View

Shows all entities related to one or more anchor entities, providing a complete narrative around a task, project, or tag:

```sh
gran view story --task 1
gran view story --project work.reports
gran view story --tag sprint-5
```

At least one anchor is required. Multiple anchors use AND logic.

| Option | Short | Description |
|---|---|---|
| `--task` | `-T` | Anchor task ID (repeatable) |
| `--time-audit` | `-A` | Anchor time audit ID (repeatable) |
| `--event` | `-E` | Anchor event ID (repeatable) |
| `--project` | `-p` | Anchor project (repeatable, exact match) |
| `--tag` | `-t` | Anchor tag (repeatable) |
| `--start` | `-s` | Override start date |
| `--end` | `-e` | Override end date |
| `--only-active-days/--all-days` | | Default: active days only |

Toggle display of each entity type with `--show-tasks/--no-tasks`, `--show-time-audits/--no-time-audits`, `--show-events/--no-events`, `--show-timespans/--no-timespans`, `--show-logs/--no-logs`, `--show-notes/--no-notes`, `--show-entries/--no-entries`.

### Heatmaps

```sh
# Task completion and time audit activity heatmap
gran view tasks-heatmap [options]

# Tracker activity heatmap
gran view tracker-heatmap [options]
```

| Option | Short | Description |
|---|---|---|
| `--days` | `-d` | Number of days (default: 14) |
| `--left-width` | `-lw` | Label column width (default: 30) |
| `--tag` | `-t` | Show separate rows per tag (repeatable) |
| `--project` | `-p` | Show separate rows per project (repeatable, tasks-heatmap only) |
| `--no-tag` | `-nt` | Exclude entities with these tags (tasks-heatmap only) |

### Tracker Views

```sh
gran view tracker-today          # Today's status for all active trackers
gran view tracker-summary <id>   # Summary for a tracker over a date range
gran view trackers               # List all trackers
gran view entries <tracker_id>   # List entries for a tracker
```

`tracker-summary` options: `--days`/`-d` (default: 14), `--start`/`-s`, `--end`/`-e`.

---

## Custom Views

Custom views let you compose multiple sub-views into a single named command. Define them in `custom-views.yaml` in your data directory under the `custom_views` key.

> **Migration note:** If you are upgrading from a previous version that used `reports.yaml`, the file is automatically renamed to `custom-views.yaml` and the YAML key is updated to `custom_views` on first run. No manual action is required.

### Defining Custom Views

```yaml
custom_views:
  - name: dashboard
    views:
      - view_type: header

      - view_type: markdown
        markdown: "## Tasks"

      - view_type: task
        columns: [id, description, project, tags, priority, due]
        filter:
          filter_type: and
          predicates:
            - filter_type: empty
              property: completed
            - filter_type: empty
              property: deleted
        sort: [priority, due]

      - view_type: space

      - view_type: markdown
        markdown: "## Upcoming"

      - view_type: agenda
        num_days: 3
        only_active_days: true
        show_scheduled_tasks: true
        show_events: true
```

Once defined, invoke with:

```sh
gran custom-view dashboard
# or using the alias:
gran cv dashboard
```

### Sub-View Types

| Type | Description |
|---|---|
| `task` | Task table with configurable columns, sort, and filter |
| `time_audit` | Time audit table |
| `event` | Event table |
| `timespan` | Timespan table |
| `log` | Log table |
| `agenda` | Agenda view with all its options |
| `gantt` | Gantt chart |
| `story` | Story view with anchor configuration |
| `tasks_heatmap` | Task/time audit heatmap |
| `markdown` | Render a markdown string |
| `header` | Render the context/view header |
| `space` | Render an empty line |

**Entity table sub-views** (`task`, `time_audit`, `event`, `timespan`, `log`) support:

| Field | Type | Description |
|---|---|---|
| `columns` | `list[str]` | Columns to display |
| `sort` | `list[str]` | Sort fields |
| `filter` | object | [Filter DSL](#filter-dsl) object |
| `include_deleted` | `bool` | Show deleted entities |
| `no_header` | `bool` | Suppress the view header |
| `no_color` | `bool` | Disable entity colors |
| `no_wrap` | `bool` | Disable text wrapping |

---

## Filter DSL

Filters are used in [Contexts](#contexts) and [Custom Views](#custom-views) to control which entities are displayed. Filters are defined as YAML objects with a recursive, composable structure.

### Boolean Filters

**AND** — all predicates must match:

```yaml
filter_type: and
predicates:
  - filter_type: tag
    filter: "work"
  - filter_type: empty
    property: completed
```

**OR** — any predicate can match:

```yaml
filter_type: or
predicates:
  - filter_type: tag
    filter: "urgent"
  - filter_type: date
    property: due
    filter: "before tomorrow"
```

**NOT** — negates a single predicate:

```yaml
filter_type: not
predicate:
  filter_type: tag
  filter: "archived"
```

### Property Filters

**String filter** — match a string property:

```yaml
filter_type: str
property: project
filter: "equals MyProject"
```

Instructions: `equals`, `equals_no_case`, `contains`, `contains_no_case`

**String regex** — regex match on a string property:

```yaml
filter_type: str_regex
property: description
filter: "^[A-Z].*bug"
```

**Date filter** — compare a date property:

```yaml
filter_type: date
property: scheduled
filter: "on today"
```

Instructions: `on` (same day), `before`, `after`
Values: `today`, `yesterday`, `tomorrow`, or any date string parseable by Pendulum

**Empty** — test if a property is null:

```yaml
filter_type: empty
property: completed
```

### Tag Filters

**Exact tag match:**

```yaml
filter_type: tag
filter: "work"
```

**Regex tag match:**

```yaml
filter_type: tag_regex
filter: "^sprint-.*"
```

---

## Date and Time Input

All date/time options across commands accept these formats:

| Input | Result |
|---|---|
| `YYYY-MM-DD` | Specific date (start of day) |
| `YYYY-MM-DD HH:mm` | Specific date and time |
| `HH:mm` or `H:mm` | Today at the given time |
| Integer (e.g., `1`, `-1`, `365`) | Day offset from today |
| `now` or `n` | Current date and time |
| `today` or `t` | Start of today |
| `yesterday` or `y` | Start of yesterday |
| `tomorrow` or `o` | Start of tomorrow |

Examples:

```sh
gran task add "Meeting prep" --due tomorrow
gran task add "Review" --scheduled 2026-03-15
gran task add "Call" --due 3              # 3 days from now
gran audit add "Deep work" --start 9:00
```

---

## ID Ranges

Commands that operate on entities by ID accept flexible ID input:

| Format | Example | Meaning |
|---|---|---|
| Single ID | `1` | Entity 1 |
| Comma-separated | `1,2,3` | Entities 1, 2, and 3 |
| Range | `1-5` | Entities 1 through 5 |
| Mixed | `1,3-5,8` | Entities 1, 3, 4, 5, and 8 |

```sh
gran task complete 1,3-5     # Complete tasks 1, 3, 4, and 5
gran task modify 1-10 --add-tag sprint-3
```

---

## Configuration

Configuration is stored in `config.yaml` inside your platform's config directory (determined by [platformdirs](https://pypi.org/project/platformdirs/)).

View current configuration:

```sh
gran config view
```

Update configuration:

```sh
gran config set --clear-ids-on-view
gran config set --data-path /path/to/my/data
gran config set --random-color-for-tasks
```

### Configuration Options

| Key | Type | Default | Description |
|---|---|---|---|
| `use_git_versioning` | bool | `false` | Auto-commit all data changes to git |
| `show_header` | bool | `true` | Show context/view header in output |
| `ical_sync_weeks` | int | `4` | Weeks ahead to sync for iCal integration |
| `ics_paths` | list | `null` | Paths to .ics files for event sync |
| `random_color_for_tasks` | bool | `false` | Auto-assign random colors to new tasks |
| `random_color_for_time_audits` | bool | `false` | Auto-assign random colors to new time audits |
| `random_color_for_events` | bool | `false` | Auto-assign random colors to new events |
| `random_color_for_timespans` | bool | `false` | Auto-assign random colors to new timespans |
| `random_color_for_logs` | bool | `false` | Auto-assign random colors to new logs |
| `data_path` | string | `null` | Custom data directory path (overrides platform default) |
| `clear_ids_on_view` | bool | `true` | Reset synthetic ID map before each view command |
| `cache_view` | bool | `false` | Cache last viewed dispatch for re-display |
| `external_notes_by_default` | bool | unset | Create notes as external markdown files by default |
| `note_timestamp_prefix_format` | string | unset | Pendulum format string for external note filename prefix |
| `sync_note_frontmatter` | bool | unset | Sync entity metadata to YAML frontmatter in external notes |

### External Notes

Notes can be stored as markdown files on disk instead of inline in the YAML data files. Configure note folders:

```sh
gran config note-folder add --name personal --path ~/notes/personal
gran config note-folder add --name work --path ~/notes/work
```

Then create external notes:

```sh
gran note add --external --folder work
gran task note 1 --external --folder personal
```

If `external_notes_by_default` is enabled, all notes will be created as external files. When `sync_note_frontmatter` is enabled, entity metadata (tags, project, references) is synced to YAML frontmatter in the markdown files.

### iCal Sync

Sync events from .ics files or URLs:

```sh
# Configure iCal sources
gran config set --ics-path /path/to/calendar.ics
gran config set --ics-path https://example.com/calendar.ics

# Sync events
gran event sync-ics

# Clean up synced events
gran event hard-delete-ics-events
```

The sync imports events for the configured number of weeks ahead (`ical_sync_weeks`, default: 4). Existing synced events are matched and updated by their iCal UID, source, and time range.

### Git Versioning

Enable automatic git versioning of your data directory:

```sh
gran config set --use-git-versioning
```

This initializes a git repository in your data directory and creates a commit after every data change. The `id_map.yaml` file is excluded from versioning (it is session-specific). Requires `git` to be available on your PATH.

---

## Command Aliases

Every command group and subcommand has a short alias for faster typing:

### Top-Level Groups

| Command | Alias |
|---|---|
| `config` | `c` |
| `context` | `cx` |
| `task` | `t` |
| `audit` | `a` |
| `event` | `e` |
| `timespan` | `ts` |
| `note` | `n` |
| `log` | `l` |
| `tracker` | `tr` |
| `view` | `v` |
| `custom-view` | `cv` |
| `search` | `s` |
| `version` | `ve` |

### Common Subcommands

| Subcommand | Alias |
|---|---|
| `add` | `a` |
| `modify` | `m` |
| `complete` | `c` / `co` |
| `delete` | `d` |
| `stop` | `s` |
| `clone` | `cl` |
| `track` | `tr` |
| `log` | `lg` |
| `note` | `nt` |
| `color` | `co` |
| `activate` | `t` |
| `archive` | `ar` |
| `unarchive` | `ua` |
| `entry` | `e` |
| `entry-modify` | `em` |
| `entry-delete` | `ed` |

**Examples:**

```sh
gran t a "My task"           # gran task add "My task"
gran a a "Working"           # gran audit add "Working"
gran a s                     # gran audit stop
gran t c 1                   # gran task complete 1
gran v ts                    # gran view tasks
gran v cd                    # gran view cal-day
gran s "query"               # gran search "query"
```

---

## Data Storage

All data is stored as plain YAML files on disk — no database is required. The default data directory is determined by [platformdirs](https://pypi.org/project/platformdirs/) and can be overridden with `gran config set --data-path`.

| File | Contents |
|---|---|
| `tasks.yaml` | All tasks |
| `time_audits.yaml` | All time audits |
| `events.yaml` | All events |
| `timespans.yaml` | All timespans |
| `notes.yaml` | All notes |
| `logs.yaml` | All logs |
| `trackers.yaml` | All trackers |
| `entries.yaml` | All tracker entries |
| `contexts.yaml` | All contexts |
| `tags.yaml` | Tag index |
| `projects.yaml` | Project index |
| `custom-views.yaml` | Custom view definitions |
| `id_map.yaml` | Synthetic-to-real ID mapping (session-specific) |
| `migrate.yaml` | Migration version state |

Data files use lazy loading and in-memory caching for performance, flushed to disk on exit.

### Global Options

These options apply to all commands:

| Option | Short | Description |
|---|---|---|
| `--no-header` | `-nh` | Suppress the context/view header |
| `--clear-ids/--no-clear-ids` | | Reset the synthetic ID map |

---

## Acknowledgements

Granular would not be possible without the prior art of CLI and text-based task management systems:

- [Taskwarrior](https://taskwarrior.org/)
- [Timewarrior](https://timewarrior.net/)
- [dstask](https://github.com/naggie/dstask)
- [Org-mode](https://orgmode.org/)
