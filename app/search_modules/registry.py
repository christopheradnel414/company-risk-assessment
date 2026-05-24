from typing import List, Type

from app.search_modules.base import BaseSearchModule
from app.search_modules.companies_house.companies_house import CompaniesHouseModule

# ── Registry ───────────────────────────────────────────────────────────────────
# To add a new module: import it here and append to ALL_MODULE_CLASSES.
# Jurisdiction filtering is handled by each module's applies_to() method.

ALL_MODULE_CLASSES: List[Type[BaseSearchModule]] = [
    CompaniesHouseModule,
]


def get_all_modules(jurisdiction: str) -> List[BaseSearchModule]:
    """Return instantiated modules applicable to the given jurisdiction."""
    return [cls() for cls in ALL_MODULE_CLASSES if cls().applies_to(jurisdiction)]
