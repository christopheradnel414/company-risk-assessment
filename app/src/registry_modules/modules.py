from typing import List, Type

from app.src.registry_modules.base import BaseRegistryModule
from app.src.registry_modules.companies_house.companies_house import CompaniesHouseRegistryModule

ALL_REGISTRY_CLASSES: List[Type[BaseRegistryModule]] = [
    CompaniesHouseRegistryModule,   # GB only
]


def get_registry_modules(jurisdiction: str) -> List[BaseRegistryModule]:
    """Return instantiated registry (disambiguation) modules for the given jurisdiction."""
    return [cls() for cls in ALL_REGISTRY_CLASSES if cls().applies_to(jurisdiction)]
