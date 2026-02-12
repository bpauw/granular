# SPDX-License-Identifier: MIT

from enum import StrEnum


class FilterType(StrEnum):
    AND = "and"
    OR = "or"
    NOT = "not"
    EMPTY = "empty"
    STR = "str"
    STR_REGEX = "str_regex"
    NUM = "num"
    DATE = "date"
    TAG = "tag"
    TAG_REGEX = "tag_regex"
