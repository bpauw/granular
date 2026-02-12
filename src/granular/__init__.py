# SPDX-License-Identifier: MIT

from granular.cleanup import register_cleanup
from granular.initialize import initialize
from granular.terminal.app import run
from granular.view.custom.loader import load_custom_views


def main() -> None:
    initialize()
    load_custom_views()
    register_cleanup()
    run()


if __name__ == "__main__":
    main()
