# Changelog

## Version 0.2.0

### New

- Added `--start-date` / `-sd` option to the `cal-days` view command, allowing users to specify which date the multi-day calendar begins on instead of always starting from today
- The `cal-days` command now supports all the same date input formats as other calendar views (e.g., `YYYY-MM-DD`, `today`, `yesterday`, `tomorrow`, numeric day offsets)

### Updated

- The `cal-days` dispatch replay system now serializes and deserializes the start date for correct caching behavior
