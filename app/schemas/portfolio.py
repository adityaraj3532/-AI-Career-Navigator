import re
from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator

RESERVED_SLUGS = {
    "api",
    "admin",
    "auth",
    "public",
    "portfolio",
    "settings",
    "export",
    "login",
    "signup",
    "help",
    "support",
    "about",
    "privacy",
    "terms",
    "dashboard",
    "user",
    "users",
    "system",
    "v1",
    "v2",
    "root",
    "me",
    "test",
    "tests",
}

SLUG_REGEX = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_web_link(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    clean = v.strip()
    if not clean:
        return None
    if not (clean.startswith("http://") or clean.startswith("https://")):
        raise ValueError("Link must begin with http:// or https://")
    if len(clean) > 2048:
        raise ValueError("Link cannot exceed 2048 characters")
    return clean


class PortfolioVisibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    about: bool = False
    skills: bool = False
    projects: bool = False
    certificates: bool = False
    competitions: bool = False
    achievements: bool = False


class ProjectItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=1000)
    skills: List[str] = Field(default_factory=list, max_length=10)
    link: Optional[str] = Field(None, max_length=2048)
    completed_date: Optional[str] = Field(None, max_length=32)
    provenance: Literal["self_reported", "test_assessed", "roadmap"] = "self_reported"

    @field_validator("link")
    @classmethod
    def check_link(cls, v: Optional[str]) -> Optional[str]:
        return validate_web_link(v)

    @field_validator("skills")
    @classmethod
    def check_skills(cls, v: List[str]) -> List[str]:
        return [s.strip()[:30] for s in v if s.strip()]


class CertificateItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=120)
    issuer: str = Field(..., min_length=1, max_length=100)
    credential_url: Optional[str] = Field(None, max_length=2048)
    issue_date: Optional[str] = Field(None, max_length=32)
    provenance: str = "self_reported"

    @field_validator("credential_url")
    @classmethod
    def check_url(cls, v: Optional[str]) -> Optional[str]:
        return validate_web_link(v)


class CompetitionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=120)
    award_or_rank: str = Field(..., min_length=1, max_length=60)
    description: Optional[str] = Field(None, max_length=500)
    year: int = Field(..., ge=2000, le=2100)


class AchievementItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    date: Optional[str] = Field(None, max_length=32)


class PortfolioProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    name: Optional[str] = None
    email: str
    education_level: Optional[str] = None
    target_career: Optional[str] = None
    subjects_of_interest: List[str] = Field(default_factory=list)


class PortfolioSkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: UUID
    slug: str
    name: str
    current_level: str
    confidence: str
    evidence_count: int = 0
    provenance: Literal["test_assessed", "self_reported"] = "self_reported"
    updated_at: datetime


class PortfolioCompletedRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    item_type: str
    title: str
    provider: Optional[str] = None
    source_url: Optional[str] = None
    completed_at: datetime


class PortfolioCompletedMilestone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: UUID
    roadmap_id: UUID
    type: str
    title: str
    topic: str
    difficulty: int
    source_url: Optional[str] = None
    completed_at: Optional[datetime] = None


class PortfolioDiagnosticTest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    type: str
    topic: str
    demonstrated_level: Optional[str] = None
    confidence: Optional[str] = None
    score_percentage: Optional[int] = None
    completed_at: Optional[datetime] = None


class PortfolioSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_skills_tracked: int
    total_recommendations_completed: int
    total_milestones_completed: int
    total_tests_completed: int


class PortfolioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: PortfolioProfile
    summary: PortfolioSummary
    skills: List[PortfolioSkillItem]
    completed_recommendations: List[PortfolioCompletedRecommendation]
    completed_milestones: List[PortfolioCompletedMilestone]
    diagnostic_tests: List[PortfolioDiagnosticTest]


class UpdatePortfolioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: Optional[str] = None
    is_public: Optional[bool] = None
    headline: Optional[str] = Field(None, max_length=160)
    about: Optional[str] = Field(None, max_length=3000)
    visibility: Optional[PortfolioVisibility] = None
    featured_item_ids: Optional[List[UUID]] = Field(None, max_length=20)
    custom_projects: Optional[List[ProjectItem]] = Field(None, max_length=20)
    custom_certificates: Optional[List[CertificateItem]] = Field(None, max_length=20)
    competitions: Optional[List[CompetitionItem]] = Field(None, max_length=20)
    achievements: Optional[List[AchievementItem]] = Field(None, max_length=20)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().lower()
        if len(clean) < 3 or len(clean) > 40:
            raise ValueError("Slug must be between 3 and 40 characters long")
        if not SLUG_REGEX.match(clean):
            raise ValueError("Slug must consist of lowercase letters, numbers, and hyphens without leading/trailing/consecutive hyphens")
        if clean in RESERVED_SLUGS:
            raise ValueError(f"Slug '{clean}' is a reserved system keyword and cannot be used")
        return clean


class OwnerPortfolioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_persisted: bool
    slug: str
    is_public: bool
    headline: Optional[str] = None
    about: Optional[str] = None
    visibility: PortfolioVisibility
    featured_item_ids: List[UUID]
    skills: List[PortfolioSkillItem]
    projects: List[ProjectItem]
    certificates: List[CertificateItem]
    competitions: List[CompetitionItem]
    achievements: List[AchievementItem]
    updated_at: Optional[datetime] = None


class PublicSkillItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    current_level: str
    confidence: str
    provenance: str


class PublicPortfolioViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    headline: Optional[str] = None
    about: Optional[str] = None
    skills: Optional[List[PublicSkillItem]] = None
    projects: Optional[List[ProjectItem]] = None
    certificates: Optional[List[CertificateItem]] = None
    competitions: Optional[List[CompetitionItem]] = None
    achievements: Optional[List[AchievementItem]] = None


class GeneratePortfolioTextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: Literal["about", "project_description"]
    user_facts: List[str] = Field(..., min_length=1, max_length=10)
    target_career: Optional[str] = Field(None, max_length=100)

    @field_validator("user_facts")
    @classmethod
    def validate_facts(cls, v: List[str]) -> List[str]:
        cleaned = []
        for fact in v:
            clean = fact.strip()
            if not clean:
                continue
            if len(clean) > 200:
                raise ValueError("Each fact must be at most 200 characters")
            cleaned.append(clean)
        if not cleaned:
            raise ValueError("At least one non-empty fact is required")
        return cleaned


class GeneratePortfolioTextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str
    generated_text: str
    is_suggestion: bool = True
    word_count: int


# Legacy / Profile public schemas
class PortfolioSummaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: Optional[str] = Field(None, max_length=120)


class PortfolioSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elevator_pitch: str
    key_highlights: List[str]
    suggested_tagline: str


class ResumeExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown_resume: str
    export_format: str = "markdown"
    generated_at: datetime
