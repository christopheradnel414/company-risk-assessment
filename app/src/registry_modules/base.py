from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar, List, Optional

from app.src.models.context import SearchContext

if TYPE_CHECKING:
    from app.src.models.response import CandidateCompany


class BaseRegistryModule(ABC):
    module_id: ClassVar[str]
    module_name: ClassVar[str]
    jurisdictions: ClassVar[Optional[List[str]]] = None

    @abstractmethod
    async def search_companies(self, context: SearchContext) -> List["CandidateCompany"]:
        """
        Search the registry for companies matching the context.

        Return a list of candidates — typically 1 when a registration_number is
        provided, or 0–many when searching by name only. May raise on error;
        callers use asyncio.gather(return_exceptions=True) to capture failures.
        """
        ...

    def applies_to(self, jurisdiction: str) -> bool:
        if self.jurisdictions is None:
            return True
        return jurisdiction.upper() in {j.upper() for j in self.jurisdictions}
