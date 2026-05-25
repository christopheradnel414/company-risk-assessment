from abc import ABC, abstractmethod
from typing import Any, ClassVar, List, Optional

from pydantic import BaseModel

from app.src.models.context import SearchContext


class SearchModuleResult(BaseModel):
    """Raw result returned by a module's fetch() method before LLM parsing."""

    raw_data: Optional[Any] = None
    error: Optional[str] = None


class BaseSearchModule(ABC):
    module_id: ClassVar[str]
    module_name: ClassVar[str]
    description: ClassVar[str]
    jurisdictions: ClassVar[Optional[List[str]]] = None
    output_schema: ClassVar[Optional[dict]] = None
    skip_llm_parsing: ClassVar[bool] = False
    system_prompt: ClassVar[str] = (
        "You are a company research analyst. "
        "Extract and structure all relevant information from the provided raw data as JSON."
    )


    @abstractmethod
    async def fetch(self, context: SearchContext) -> SearchModuleResult:
        """
        Fetch raw data from the external source.

        Must handle its own exceptions — return SearchModuleResult with an
        `error` string rather than raising.
        """
        ...

    def applies_to(self, jurisdiction: str) -> bool:
        """Return True if this module should run for the given jurisdiction."""
        if self.jurisdictions is None:
            return True
        return jurisdiction.upper() in {j.upper() for j in self.jurisdictions}
