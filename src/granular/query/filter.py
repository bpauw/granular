# SPDX-License-Identifier: MIT

import re
from abc import ABC, abstractmethod
from typing import Any, Optional, cast

import pendulum

from granular.model.filter import (
    BooleanFilter,
    Filter,
    Filters,
    PropertyFilter,
    PropertyNameFilter,
    SingleBooleanFilter,
    ValueFilter,
)
from granular.query.filter_type import FilterType
from granular.query.util import split_instruction


def generate_filter(filter: Filters) -> "Predicate":
    filter_obj = filter_factory(filter)
    if isinstance(filter_obj, And | Or):
        for child_filter_bool in cast(BooleanFilter, filter)["predicates"]:
            filter_obj.add_predicate(generate_filter(child_filter_bool))
    elif isinstance(filter_obj, Not):
        child_filter_single_bool = cast(SingleBooleanFilter, filter)["predicate"]
        filter_obj.set_predicate(generate_filter(child_filter_single_bool))
    return filter_obj


def filter_factory(filter: Filter) -> "Predicate":
    match filter["filter_type"]:
        case FilterType.AND:
            return And()
        case FilterType.OR:
            return Or()
        case FilterType.NOT:
            return Not()
        case FilterType.EMPTY:
            return Empty(cast(PropertyNameFilter, filter))
        case FilterType.STR:
            return Str(cast(PropertyFilter, filter))
        case FilterType.STR_REGEX:
            return StrRegex(cast(PropertyFilter, filter))
        case FilterType.DATE:
            return Date(cast(PropertyFilter, filter))
        case FilterType.TAG:
            return Tag(cast(ValueFilter, filter))
        case FilterType.TAG_REGEX:
            return TagRegex(cast(ValueFilter, filter))
    raise Exception()


class Predicate(ABC):
    @abstractmethod
    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


class And(Predicate):
    def __init__(self) -> None:
        self.predicates: list[Predicate] = []

    def add_predicate(self, predicate: Predicate) -> None:
        self.predicates.append(predicate)

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result_ids = [item["id"] for item in items]
        for predicate in self.predicates:
            pred_results = predicate.filter(items)
            pred_result_ids = [pred_result["id"] for pred_result in pred_results]
            result_ids = [id for id in result_ids if id in pred_result_ids]
        return [item for item in items if item["id"] in result_ids]


class Or(Predicate):
    def __init__(self) -> None:
        self.predicates: list[Predicate] = []

    def add_predicate(self, predicate: Predicate) -> None:
        self.predicates.append(predicate)

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for predicate in self.predicates:
            pred_results = predicate.filter(items)
            results += pred_results
        return list(results)


class Not(Predicate):
    def __init__(self) -> None:
        self.predicate: Optional[Predicate] = None

    def set_predicate(self, predicate: Predicate) -> None:
        self.predicate = predicate

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.predicate is None:
            raise ValueError("NOT predicate cannot be None")
        predicate_items = self.predicate.filter(items)
        predicate_item_ids = {item["id"] for item in predicate_items}
        result = [item for item in items if item["id"] not in predicate_item_ids]
        return result


class Empty(Predicate):
    def __init__(self, property_filter: PropertyNameFilter) -> None:
        self.property_filter = property_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            item
            for item in items
            if self.property_filter["property"] in item
            and item[self.property_filter["property"]] is None
        ]


class Str(Predicate):
    def __init__(self, property_filter: PropertyFilter) -> None:
        self.property_filter = property_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_items = []

        for item in items:
            if self.__include(item):
                filtered_items.append(item)

        return filtered_items

    def __include(self, item: dict[str, Any]) -> bool:
        property = self.property_filter["property"]
        instruction, value = split_instruction(self.property_filter["filter"])

        if property in item:
            if item[property] is not None:
                match instruction:
                    case "equals":
                        return str(item[property]) == value
                    case "equals_no_case":
                        return str(item[property]).lower() == value.lower()
                    case "contains":
                        return value in str(item[property])
                    case "contains_no_case":
                        return value.lower() in str(item[property]).lower()
        return False


class StrRegex(Predicate):
    def __init__(self, property_filter: PropertyFilter) -> None:
        self.property_filter = property_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_items = []

        pattern = re.compile(self.property_filter["filter"])

        for item in items:
            if self.property_filter["property"] in item:
                if pattern.search(item[self.property_filter["property"]]):
                    filtered_items.append(item)

        return filtered_items


class Date(Predicate):
    def __init__(self, property_filter: PropertyFilter) -> None:
        self.property_filter = property_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_tasks = []

        for item in items:
            if self.__include(item):
                filtered_tasks.append(item)

        return filtered_tasks

    def __include(self, item: dict[str, Any]) -> bool:
        property = self.property_filter["property"]
        instruction, value = split_instruction(self.property_filter["filter"])

        if property in item:
            if item[property] is not None:
                reference_date: pendulum.DateTime = pendulum.today()
                match value:
                    case "today":
                        reference_date = pendulum.today()
                    case "yesterday":
                        reference_date = reference_date.subtract(days=1)
                    case "tomorrow":
                        reference_date = reference_date.add(days=1)
                    case _:
                        reference_date = cast(pendulum.DateTime, pendulum.parse(value))

                match instruction:
                    case "on":
                        end_reference_date = reference_date.add(
                            hours=23, minutes=59, seconds=59
                        )
                        return (
                            reference_date
                            <= cast(pendulum.DateTime, item[property])
                            < end_reference_date
                        )
                    case "before":
                        return cast(pendulum.DateTime, item[property]) < reference_date
                    case "after":
                        return cast(pendulum.DateTime, item[property]) > reference_date
        return False


class Tag(Predicate):
    def __init__(self, tag_filter: ValueFilter) -> None:
        self.tag_filter = tag_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_items = []

        for item in items:
            if "tags" in item and item["tags"] is not None:
                if self.tag_filter["filter"] in item["tags"]:
                    filtered_items.append(item)

        return filtered_items


class TagRegex(Predicate):
    def __init__(self, tag_filter: ValueFilter) -> None:
        self.tag_filter = tag_filter

    def filter(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered_items = []
        pattern = re.compile(self.tag_filter["filter"])

        for item in items:
            if "tags" in item and item["tags"] is not None:
                if any(pattern.search(tag) for tag in item["tags"]):
                    filtered_items.append(item)

        return filtered_items


def tag_matches_regex(pattern: str, entity_tags: list[str]) -> bool:
    """Check if a regex pattern matches any of the entity's tags."""
    compiled = re.compile(pattern)
    return any(compiled.search(tag) for tag in entity_tags)
