# SPDX-License-Identifier: MIT

from typing import TypedDict

from granular.query.filter_type import FilterType


class Filter(TypedDict):
    filter_type: FilterType


class BooleanFilter(Filter):
    predicates: list["Filters"]


class SingleBooleanFilter(Filter):
    predicate: "Filters"


class PropertyFilter(Filter):
    property: str
    filter: str


class PropertyNameFilter(Filter):
    property: str


class ValueFilter(Filter):
    filter: str


Filters = (
    BooleanFilter
    | SingleBooleanFilter
    | PropertyFilter
    | PropertyNameFilter
    | ValueFilter
)
