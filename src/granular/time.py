# SPDX-License-Identifier: MIT

import datetime
from typing import Optional, cast

import pendulum


def now_utc() -> pendulum.DateTime:
    return pendulum.now("UTC")


def python_to_pendulum_utc(python_value: datetime.datetime) -> pendulum.DateTime:
    pendulum_value = pendulum.instance(python_value, tz="local")
    return pendulum_value.in_tz("UTC")


def python_to_pendulum_utc_optional(
    python_value: Optional[datetime.datetime],
) -> Optional[pendulum.DateTime]:
    if python_value is None:
        return None
    return python_to_pendulum_utc(python_value)


def datetime_to_iso_str(datetime: pendulum.DateTime) -> str:
    return datetime.isoformat()


def datetime_to_iso_str_optional(
    datetime: Optional[pendulum.DateTime],
) -> Optional[str]:
    if datetime is None:
        return None
    return datetime_to_iso_str(datetime)


def datetime_to_display_local_date_str(datetime: pendulum.DateTime) -> str:
    return datetime.in_tz("local").format("YYYY-MM-DD ddd")


def datetime_to_display_local_date_str_optional(
    datetime: Optional[pendulum.DateTime],
) -> Optional[str]:
    if datetime is None:
        return None
    return datetime_to_display_local_date_str(datetime)


def datetime_to_display_local_datetime_str(datetime: pendulum.DateTime) -> str:
    return datetime.in_tz("local").format("MMM-DD ddd HH:mm")


def datetime_to_display_local_datetime_str_optional(
    datetime: Optional[pendulum.DateTime],
) -> Optional[str]:
    if datetime is None:
        return None
    return datetime_to_display_local_datetime_str(datetime)


def datetime_from_str(datetime: str) -> pendulum.DateTime:
    return cast(pendulum.DateTime, pendulum.parse(datetime))


def datetime_from_str_optional(datetime: Optional[str]) -> Optional[pendulum.DateTime]:
    if datetime is None:
        return None
    return datetime_from_str(datetime)


def datetime_from_str_utc(datetime: str) -> pendulum.DateTime:
    pendulum_date_time = cast(pendulum.DateTime, pendulum.parse(datetime))
    pendulum_date_time = pendulum_date_time.set(tz="local")
    pendulum_date_time = pendulum_date_time.in_tz("UTC")
    return pendulum_date_time


def duration_to_str(duration: pendulum.Duration) -> str:
    return f"{duration.hours}:{duration.minutes}"


def duration_to_str_optional(duration: Optional[pendulum.Duration]) -> Optional[str]:
    if duration is None:
        return None
    return duration_to_str(duration)


def duration_from_str(duration: str) -> pendulum.Duration:
    hours, minutes = map(int, duration.split(":"))
    return pendulum.duration(hours=hours, minutes=minutes)


def duration_from_str_optional(duration: Optional[str]) -> Optional[pendulum.Duration]:
    if duration is None:
        return None
    return duration_from_str(duration)


def datetime_to_local_date_str(datetime: pendulum.DateTime) -> str:
    """Convert a pendulum.DateTime to a local date string in 'YYYY-MM-DD' format."""
    return datetime.in_tz("local").format("YYYY-MM-DD")


def datetime_to_local_date_str_optional(
    datetime: Optional[pendulum.DateTime],
) -> Optional[str]:
    """Convert an optional pendulum.DateTime to a local date string in 'YYYY-MM-DD' format."""
    if datetime is None:
        return None
    return datetime_to_local_date_str(datetime)


def datetime_from_local_date_str(date_str: str) -> pendulum.DateTime:
    """Parse a local date string in 'YYYY-MM-DD' format to a pendulum.DateTime at midnight local time."""
    return cast(pendulum.DateTime, pendulum.parse(date_str, tz="local"))


def datetime_from_local_date_str_optional(
    date_str: Optional[str],
) -> Optional[pendulum.DateTime]:
    """Parse an optional local date string in 'YYYY-MM-DD' format to a pendulum.DateTime."""
    if date_str is None:
        return None
    return datetime_from_local_date_str(date_str)
