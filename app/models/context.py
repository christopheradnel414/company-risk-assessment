from typing import Optional

from pydantic import BaseModel


class SearchContext(BaseModel):
    """Carries the user-supplied identifiers for a company through the search pipeline."""

    company_name: Optional[str] = None
    registration_number: Optional[str] = None
    jurisdiction: str
