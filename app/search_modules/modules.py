from typing import List, Type

from app.search_modules.base import BaseSearchModule
from app.search_modules.companies_house.companies_house import CompaniesHouseModule

ALL_SEARCH_MODULES: List[Type[BaseSearchModule]] = [
    CompaniesHouseModule, # GB Only
]


def get_all_modules(jurisdiction: str) -> List[BaseSearchModule]:
    """Return instantiated modules applicable to the given jurisdiction."""
    return [cls() for cls in ALL_SEARCH_MODULES if cls().applies_to(jurisdiction)]
