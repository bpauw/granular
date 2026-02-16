# Changelog

## Version 0.3.0

### New

- Added `gran custom-view` (alias `gran cv`) top-level command group for user-defined compound views, separating them from the built-in `gran view` commands
- Added data migration to automatically rename `reports.yaml` to `custom-views.yaml` and update the YAML key for existing users

### Updated

- Custom views are now defined under the `custom_views` key in `custom-views.yaml` (previously `views` or `reports` key in `reports.yaml`)
- The `gran --help` output now lists `custom-view, cv` after `view, v` and includes the previously missing `version, ve` entry

## Version 0.2.0

### New

- Added `--start-date` / `-sd` option to the `cal-days` view command, allowing users to specify which date the multi-day calendar begins on instead of always starting from today
- The `cal-days` command now supports all the same date input formats as other calendar views (e.g., `YYYY-MM-DD`, `today`, `yesterday`, `tomorrow`, numeric day offsets)

### Updated

- The `cal-days` dispatch replay system now serializes and deserializes the start date for correct caching behavior
