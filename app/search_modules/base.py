from abc import ABC, abstractmethod
from typing import Any, ClassVar, List, Optional

from pydantic import BaseModel

from app.models.context import SearchContext


class SearchModuleResult(BaseModel):
    """Raw result returned by a module's fetch() method before LLM parsing."""

    raw_data: Optional[Any] = None
    error: Optional[str] = None


class BaseSearchModule(ABC):
    """
    Abstract base class for all search modules.

    ## Adding a new module
    1. Create a new file in `app/search_modules/`
    2. Subclass `BaseSearchModule`
    3. Set `module_id`, `module_name`, `description` and optionally `jurisdictions`
    4. Define `output_schema` (JSON Schema dict) for validation and LLM guidance
    5. If fetch() already returns data matching output_schema, set skip_llm_parsing=True
    6. Implement `fetch(context)`
    7. Register the class in `app/search_modules/registry.py`
    """

    # ── Required class-level attributes ───────────────────────────────────────

    module_id: ClassVar[str]
    module_name: ClassVar[str]
    description: ClassVar[str]

    # ── Optional configuration ─────────────────────────────────────────────────

    jurisdictions: ClassVar[Optional[List[str]]] = None
    """ISO 3166-1 alpha-2 codes this module applies to.  None = all jurisdictions."""

    output_schema: ClassVar[Optional[dict]] = None
    """JSON Schema dict used for LLM guidance and output validation. None = free-form."""

    skip_llm_parsing: ClassVar[bool] = False
    """
    When True, raw_data from fetch() is used directly as the structured output —
    no LLM call is made. Set this on modules whose fetch() already returns data
    that conforms to output_schema (e.g. typed API wrappers that do their own mapping).
    """

    system_prompt: ClassVar[str] = (
        "You are a company research analyst. "
        "Extract and structure all relevant information from the provided raw data as JSON."
    )

    # ── Interface ──────────────────────────────────────────────────────────────

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
        return jurisdiction.upper() in [j.upper() for j in self.jurisdictions]
