from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List, Optional

from app.src.models.context import SearchContext

if TYPE_CHECKING:
    from app.src.models.response import CandidateCompany


class BaseRegistryModule(ABC):
    """
    Abstract base class for registry disambiguation modules.

    These run before search modules to resolve an ambiguous company name into a
    single canonical company (name + registration number). If multiple matches are
    found across all applicable registry modules, the job is paused and the caller
    is asked to resubmit with a registration number.

    ## Adding a new registry module
    1. Create a new file in `app/registry_modules/`
    2. Subclass `BaseRegistryModule`
    3. Set `module_id`, `module_name`, and `jurisdictions`
    4. Implement `search_companies(context)` — return a list of `CandidateCompany`
    5. Add the class to `ALL_REGISTRY_CLASSES` in `app/registry_modules/registry.py`
    """

    module_id: ClassVar[str]
    module_name: ClassVar[str]
    jurisdictions: ClassVar[Optional[List[str]]] = None

    @abstractmethod
    async def search_companies(self, context: SearchContext) -> List["CandidateCompany"]:
        """
        Search the registry for companies matching the context.

        Return a list of candidates — typically 1 when a registration_number is
        provided, or 0–many when searching by name only. Must not raise; return
        an empty list on failure.
        """
        ...

    def applies_to(self, jurisdiction: str) -> bool:
        if self.jurisdictions is None:
            return True
        return jurisdiction.upper() in [j.upper() for j in self.jurisdictions]
