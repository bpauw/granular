# SPDX-License-Identifier: MIT

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.migrate.registry import migration


@migration(5)
def migrate() -> None:
    print("running migration 5: converting task_id to task_ids...")

    file_path = configuration.DATA_TIME_AUDIT_PATH
    if not file_path.exists():
        print("  time_audits.yaml not found, skipping")
        return

    data = load(file_path.read_text(), Loader=Loader)
    if data is None:
        data = {"time_audits": []}

    time_audits = data.get("time_audits", [])
    converted_count = 0

    for time_audit in time_audits:
        if "task_id" in time_audit:
            old_value = time_audit.pop("task_id")
            if old_value is not None:
                time_audit["task_ids"] = [old_value]
            else:
                time_audit["task_ids"] = None
            converted_count += 1

    if converted_count > 0:
        file_path.write_text(dump(data, Dumper=Dumper))

    print(f"  time_audits: converted {converted_count} entries")
    print("migration 5 complete!")
