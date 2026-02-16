# SPDX-License-Identifier: MIT

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Dumper  # type: ignore[assignment]
    from yaml import Loader  # type: ignore[assignment]

from granular import configuration
from granular.migrate.registry import migration


@migration(2)
def migrate() -> None:
    old_path = configuration.DATA_PATH / "reports.yaml"

    if not old_path.exists():
        return

    data = load(old_path.read_text(), Loader=Loader)

    if data is None:
        data = {}

    if "reports" in data:
        data["custom_views"] = data.pop("reports")
    elif "views" in data:
        data["custom_views"] = data.pop("views")

    configuration.DATA_CUSTOM_VIEWS_PATH.write_text(dump(data, Dumper=Dumper))
    old_path.unlink()
