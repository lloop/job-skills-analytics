"""Domain models for job market analytics."""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class JobPosting:
    """Represents a standardized job posting entity."""
    
    title: str
    company: str
    salary: str | None
    description: str
    url: str
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Convert dataclass fields to a dictionary for SQL parameter binding."""
        return asdict(self)
    
# @dataclass
# class JobPosting:
#     """Normalized job posting data."""

#     title: str
#     company: str
#     salary: str | None
#     description: str
#     url: str
#     tags: tuple[str, ...] = ()