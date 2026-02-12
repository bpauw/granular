# SPDX-License-Identifier: MIT

from typing import Optional, TypeIs, cast, get_args

from yaml import dump, load

try:
    from yaml import CDumper as Dumper
    from yaml import CLoader as Loader  # noqa: F401
except ImportError:
    from yaml import Dumper, Loader  # type: ignore[assignment]

from granular import configuration
from granular.model.id_map import EntityType, IdMap, IdMapDict
from granular.template.id_map import get_id_map_template

ENTITY_TYPES = get_args(EntityType)


class IdMapRepository:
    def __init__(self) -> None:
        self._id_map: Optional[IdMap] = None
        self.is_dirty = False

    @property
    def id_map(self) -> IdMap:
        if self._id_map is None:
            self.__load_data()
        if self._id_map is None:
            raise ValueError()
        return self._id_map

    def __load_data(self) -> None:
        self._id_map = load(configuration.DATA_ID_MAP_PATH.read_text(), Loader=Loader)

    def __save_data(self, id_map: IdMap) -> None:
        configuration.DATA_ID_MAP_PATH.write_text(dump(id_map, Dumper=Dumper))

    def flush(self) -> None:
        if self._id_map is not None and self.is_dirty:
            self.__save_data(self._id_map)

    def clear_ids(self) -> None:
        self.is_dirty = True
        self._id_map = get_id_map_template()

    def associate_id(self, entity_type: str, entity_id: int) -> int:
        """
        Create a new synthetic id to associate with an entity id
        """
        self.is_dirty = True

        if self.__narrow_to_entity_type(entity_type):
            entity_type_lit = cast(EntityType, entity_type)
            id_map_dict = cast(IdMapDict, self.id_map)
            if entity_id in id_map_dict[entity_type_lit]["real_to_synthetic"].keys():
                return id_map_dict[entity_type_lit]["real_to_synthetic"][entity_id]

            next_id = len(id_map_dict[entity_type_lit]["real_to_synthetic"].keys()) + 1
            id_map_dict[entity_type_lit]["real_to_synthetic"][entity_id] = next_id
            id_map_dict[entity_type_lit]["synthetic_to_real"][next_id] = entity_id

            return next_id
        raise TypeError(
            f"{IdMapRepository.associate_id.__name__}: expected {EntityType.__name__} literals"
        )

    def get_real_id(self, entity_type: str, synthetic_id: int) -> int:
        """
        Get the entity id associated with a synthetic id
        """
        if self.__narrow_to_entity_type(entity_type):
            entity_type_lit = cast(EntityType, entity_type)
            id_map_dict = cast(IdMapDict, self.id_map)
            return id_map_dict[entity_type_lit]["synthetic_to_real"][synthetic_id]
        raise TypeError(
            f"{IdMapRepository.associate_id.__name__}: expected {EntityType.__name__} literals"
        )

    def __narrow_to_entity_type(self, entity_type: str) -> TypeIs[EntityType]:
        global ENTITY_TYPES

        return entity_type in ENTITY_TYPES


ID_MAP_REPO = IdMapRepository()
