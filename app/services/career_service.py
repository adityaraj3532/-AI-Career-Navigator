import math
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.user import User
from app.repositories.assessment_repository import AssessmentRepository
from app.repositories.career_repository import CareerRepository
from app.schemas.career import (
    CareerDetailResponse,
    CareerListItem,
    CareersListResponse,
    CertificateSummaryResponse,
    CollegeSummaryResponse,
    CourseSummaryResponse,
    EducationPathStageSchema,
    ExamSummaryResponse,
    InternshipSummaryResponse,
    RelatedCareerSummaryResponse,
    SalaryRangesSchema,
    SkillItemSchema,
)
from app.services.scoring_service import calculate_career_similarity


class CareerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CareerRepository(session)
        self.assessment_repo = AssessmentRepository(session)

    async def list_careers(
        self,
        user: Optional[User] = None,
        cluster: Optional[str] = None,
        demand: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CareersListResponse:
        # Enforce page size bounds [1, 50]
        safe_page_size = min(max(1, page_size), 50)
        safe_page = max(1, page)

        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        careers, total_count = await self.repo.list_careers(
            cluster=cluster,
            demand=demand,
            min_salary=min_salary,
            max_salary=max_salary,
            allow_drafts=allow_drafts,
            page=safe_page,
            page_size=safe_page_size,
        )

        # Check if user has completed assessment to compute compatibility score
        user_scores = None
        if user is not None:
            latest_result = await self.assessment_repo.get_latest_result(user.id)
            if latest_result:
                user_scores = latest_result.dimension_scores

        items = []
        for c in careers:
            comp_score = None
            if user_scores and c.dimension_weights:
                sim = calculate_career_similarity(user_scores, c.dimension_weights)
                comp_score = int(round(sim * 100))

            salary_schema = None
            if c.salary_ranges:
                salary_schema = SalaryRangesSchema(**c.salary_ranges)

            items.append(
                CareerListItem(
                    id=c.id,
                    code=c.code,
                    title=c.title,
                    cluster=c.cluster,
                    aliases=c.aliases or [],
                    overview=c.overview,
                    demand=c.demand,
                    salary_ranges=salary_schema,
                    status=c.status,
                    source_url=c.source_url,
                    compatibility_score=comp_score,
                )
            )

        total_pages = math.ceil(total_count / safe_page_size) if total_count > 0 else 0

        return CareersListResponse(
            items=items,
            page=safe_page,
            page_size=safe_page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def search_careers(
        self,
        query: str,
        user: Optional[User] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> CareersListResponse:
        safe_page_size = min(max(1, page_size), 50)
        safe_page = max(1, page)
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        careers, total_count = await self.repo.search_careers(
            query=query[:60],
            allow_drafts=allow_drafts,
            page=safe_page,
            page_size=safe_page_size,
        )

        user_scores = None
        if user is not None:
            latest_result = await self.assessment_repo.get_latest_result(user.id)
            if latest_result:
                user_scores = latest_result.dimension_scores

        items = []
        for c in careers:
            comp_score = None
            if user_scores and c.dimension_weights:
                sim = calculate_career_similarity(user_scores, c.dimension_weights)
                comp_score = int(round(sim * 100))

            salary_schema = None
            if c.salary_ranges:
                salary_schema = SalaryRangesSchema(**c.salary_ranges)

            items.append(
                CareerListItem(
                    id=c.id,
                    code=c.code,
                    title=c.title,
                    cluster=c.cluster,
                    aliases=c.aliases or [],
                    overview=c.overview,
                    demand=c.demand,
                    salary_ranges=salary_schema,
                    status=c.status,
                    source_url=c.source_url,
                    compatibility_score=comp_score,
                )
            )

        total_pages = math.ceil(total_count / safe_page_size) if total_count > 0 else 0
        return CareersListResponse(
            items=items,
            page=safe_page,
            page_size=safe_page_size,
            total_count=total_count,
            total_pages=total_pages,
        )

    async def get_career_detail(
        self,
        career_id: UUID,
        user: Optional[User] = None,
    ) -> CareerDetailResponse:
        settings = get_settings()
        allow_drafts = (settings.ENVIRONMENT == "development" and settings.ALLOW_DRAFT_CAREERS)

        career = await self.repo.get_by_id(career_id=career_id, allow_drafts=allow_drafts, eager_load=True)
        if not career:
            raise AppException(
                status_code=404,
                code="CAREER_NOT_FOUND",
                message=f"Career with ID '{career_id}' not found or unverified.",
            )

        comp_score = None
        if user is not None and career.dimension_weights:
            latest_result = await self.assessment_repo.get_latest_result(user.id)
            if latest_result:
                sim = calculate_career_similarity(latest_result.dimension_scores, career.dimension_weights)
                comp_score = int(round(sim * 100))

        salary_schema = None
        if career.salary_ranges:
            salary_schema = SalaryRangesSchema(**career.salary_ranges)

        skills = [SkillItemSchema(**s) for s in (career.required_skills or [])]
        education = [EducationPathStageSchema(**e) for e in (career.education_paths or [])]

        exams = [
            ExamSummaryResponse(
                id=e.id,
                code=e.code,
                name=e.name,
                description=e.description,
                conducting_body=e.conducting_body,
                exam_level=e.exam_level,
                registration_url=e.registration_url,
                source_url=e.source_url,
                status=e.status,
            )
            for e in career.exams
        ]

        colleges = [
            CollegeSummaryResponse(
                id=c.id,
                name=c.name,
                location=c.location,
                official_url=c.official_url,
                fees=c.fees,
                cutoffs=c.cutoffs,
                nirf_rank=c.nirf_rank,
                source_url=c.source_url,
                status=c.status,
            )
            for c in career.colleges
        ]

        courses = [
            CourseSummaryResponse(
                id=c.id,
                code=c.code,
                title=c.title,
                degree_level=c.degree_level,
                duration=c.duration,
                description=c.description,
                source_url=c.source_url,
                status=c.status,
            )
            for c in career.courses
        ]

        certificates = [
            CertificateSummaryResponse(
                id=c.id,
                code=c.code,
                name=c.name,
                issuing_organization=c.issuing_organization,
                description=c.description,
                url=c.url,
                source_url=c.source_url,
                status=c.status,
            )
            for c in career.certificates
        ]

        internships = [
            InternshipSummaryResponse(
                id=i.id,
                code=i.code,
                title=i.title,
                domain=i.domain,
                stipend_range=i.stipend_range,
                duration_months=i.duration_months,
                locations=i.locations or [],
                description=i.description,
                source_url=i.source_url,
                status=i.status,
            )
            for i in career.internships
        ]

        related = [
            RelatedCareerSummaryResponse(
                id=r.id,
                code=r.code,
                title=r.title,
                cluster=r.cluster,
                overview=r.overview,
                demand=r.demand,
            )
            for r in career.related_careers
        ]

        return CareerDetailResponse(
            id=career.id,
            code=career.code,
            title=career.title,
            cluster=career.cluster,
            aliases=career.aliases or [],
            overview=career.overview,
            description=career.description,
            day_in_life=career.day_in_life,
            demand=career.demand,
            salary_ranges=salary_schema,
            required_skills=skills,
            education_paths=education,
            dimension_weights=career.dimension_weights,
            status=career.status,
            source_url=career.source_url,
            reviewer=career.reviewer,
            last_verified_at=career.last_verified_at or career.verified_at,
            compatibility_score=comp_score,
            exams=exams,
            colleges=colleges,
            courses=courses,
            certificates=certificates,
            internships=internships,
            related_careers=related,
        )
