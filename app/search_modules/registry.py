from typing import List, Type

from app.search_modules.base import BaseSearchModule
from app.search_modules.adverse_media import AdverseMediaModule
from app.search_modules.companies_house import CompaniesHouseModule
from app.search_modules.icij_search import ICIJSearchModule
from app.search_modules.news_search import NewsSearchModule
from app.search_modules.open_corporates import OpenCorporatesModule
from app.search_modules.open_sanctions import OpenSanctionsModule

# ── Registry ───────────────────────────────────────────────────────────────────
# To add a new module: import it here and append to ALL_MODULE_CLASSES.
# Jurisdiction filtering is handled by each module's applies_to() method.

ALL_MODULE_CLASSES: List[Type[BaseSearchModule]] = [
    CompaniesHouseModule,   # GB only
    OpenCorporatesModule,   # global
    NewsSearchModule,       # global
    AdverseMediaModule,     # global
    ICIJSearchModule,       # global
    OpenSanctionsModule,    # global
]


def get_all_modules(jurisdiction: str) -> List[BaseSearchModule]:
    """Return instantiated modules applicable to the given jurisdiction."""
    return [cls() for cls in ALL_MODULE_CLASSES if cls().applies_to(jurisdiction)]
