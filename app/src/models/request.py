from typing import Optional

from pydantic import BaseModel, Field, model_validator


class AssessmentRequest(BaseModel):
    company_name: Optional[str] = Field(
        None,
        description="Company name to search for",
        examples=["Acme Consulting Ltd"],
    )
    registration_number: Optional[str] = Field(
        None,
        description="Official company registration / incorporation number",
        examples=["12345678"],
    )
    jurisdiction: str = Field(
        "GB",
        description="ISO 3166-1 alpha-2 country code that determines which search modules are activated",
        examples=["GB", "US", "DE"],
    )

    @model_validator(mode="after")
    def require_at_least_one_identifier(self) -> "AssessmentRequest":
        if not self.company_name and not self.registration_number:
            raise ValueError(
                "At least one of 'company_name' or 'registration_number' must be provided."
            )
        return self

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "company_name": "Acme Consulting Ltd",
                    "registration_number": "12345678",
                    "jurisdiction": "GB",
                }
            ]
        }
    }
