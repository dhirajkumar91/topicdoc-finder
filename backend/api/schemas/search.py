from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=1000,
        description="Research topic or question to search for.",
    )

    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of research papers to return.",
    )


class RelevantPassage(BaseModel):
    chunk_id: str
    chunk_index: int
    section_chunk_index: int | None = None
    section_title: str | None = None
    parent_section_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    content: str
    similarity_score: float


class RelevantTable(BaseModel):
    table_id: str
    document_id: str

    # Source document metadata
    title: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None

    # Table metadata
    table_index: int
    table_number: int | None = None
    table_title: str | None = None
    section_title: str | None = None
    parent_section_title: str | None = None
    page_start: int
    page_end: int

    # Structured table data
    column_headers: list | None = None
    table_data: list
    raw_table_data: list | None = None
    table_text: str
    footnotes: list | None = None

    similarity_score: float


class ResearchPaperResult(BaseModel):
    document_id: str
    title: str | None = None
    abstract: str | None = None
    authors: list[str] = Field(default_factory=list)
    published_date: str | None = None
    source_name: str | None = None
    source_url: str | None = None
    pdf_url: str | None = None
    similarity_score: float
    retrieved_chunk_count: int
    relevant_passages: list[RelevantPassage]
    relevant_tables: list[RelevantTable] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    total_results: int
    results: list[ResearchPaperResult]

    total_tables: int
    relevant_tables: list[RelevantTable]