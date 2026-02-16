# SPDX-License-Identifier: MIT

import typer

from granular.terminal.custom_typer import AlphabeticalContextAwareGroup

app = typer.Typer(
    cls=AlphabeticalContextAwareGroup,
    no_args_is_help=True,
    help="User-defined custom views",
)
