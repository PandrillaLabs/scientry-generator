import re

from pydantic import BaseModel, Field


class MetadataDto(BaseModel):
    doiId: str = Field(..., pattern=re.compile(r"10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", re.IGNORECASE), description="DOI ID of the article")
    title: str = Field(..., max_length=500, description="Title of the article")
    authors: list[str] = Field(..., description="List of authors of the article")
    abstractText: str = Field(..., description="Abstract text of the article")
    citation: str = Field(..., description="Citation of the article")
    citationMap: dict = Field(..., description="Citation map of the article")
    categoryId: str = Field(..., description="Category ID of the article")
    tagIds: list[str] = Field(..., description="List of tag IDs associated with the article")
    journalId: str = Field(..., description="Journal ID of the article")
    publisherId: str = Field(..., description="Publisher ID of the article")
    publishedYear: int = Field(..., ge=1900, le=2100, description="Year the article was published")
    pdfUrl: str = Field(..., description="URL to the PDF of the article")

    def json(self):
        return self.model_dump_json()