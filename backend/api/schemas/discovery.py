from pydantic import BaseModel, Field


class DiscoveryRequest(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=1000,
        description="Research topic to discover papers across academic sources.",
    )

    max_results_per_source: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum papers to retrieve from each source.",
    )


class DiscoveryPaper(BaseModel):
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_date: str | None = None
    doi: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    sources: list[str] = Field(default_factory=list)
    external_id: str | None = None


class DiscoveryResponse(BaseModel):
    query: str
    total_results: int
    results: list[DiscoveryPaper]
    source_errors: dict[str, str] = Field(default_factory=dict)