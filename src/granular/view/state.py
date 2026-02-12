"""Global application state using context variables for thread-safe state management."""

# SPDX-License-Identifier: MIT

from contextvars import ContextVar

# Context variable for controlling header visibility in reports
# Default is True (show headers)
_show_header_var: ContextVar[bool] = ContextVar("show_header", default=True)

# Context variable for controlling text wrapping in report columns
# Default is False (allow wrapping)
_no_wrap_var: ContextVar[bool] = ContextVar("no_wrap", default=False)


def set_show_header(value: bool) -> None:
    """Set whether headers should be displayed in reports.

    Args:
        value: True to show headers, False to hide them
    """
    _show_header_var.set(value)


def get_show_header() -> bool:
    """Get whether headers should be displayed in reports.

    Returns:
        True if headers should be shown, False otherwise
    """
    return _show_header_var.get()


def set_no_wrap(value: bool) -> None:
    """Set whether text wrapping should be disabled in report columns.

    Args:
        value: True to disable wrapping, False to allow wrapping
    """
    _no_wrap_var.set(value)


def get_no_wrap() -> bool:
    """Get whether text wrapping should be disabled in report columns.

    Returns:
        True if wrapping should be disabled, False otherwise
    """
    return _no_wrap_var.get()
