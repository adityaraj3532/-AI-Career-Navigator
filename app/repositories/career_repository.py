from typing import List, Optional, Tuple
from uuid import UUID
from sqlalchemy import Integer, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import Career


class CareerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_careers(self, allow_drafts: bool = False) -> List[Career]:
        """
        Retrieves careers available for scoring and recommendations.
        By default, only verified careers are returned.
        Draft careers are included only if allow_drafts is True.
        """
        stmt = select(Career)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")
        stmt = stmt.order_by(Career.title.asc(), Career.id.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_careers(
        self,
        cluster: Optional[str] = None,
        demand: Optional[str] = None,
        min_salary: Optional[int] = None,
        max_salary: Optional[int] = None,
        allow_drafts: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Career], int]:
        """
        Paginated, filtered query with stable ordering (title asc, id asc).
        """
        stmt = select(Career)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")

        if cluster:
            stmt = stmt.where(Career.cluster == cluster)

        if demand:
            stmt = stmt.where(Career.demand == demand)

        if min_salary is not None:
            stmt = stmt.where(
                or_(
                    cast(Career.salary_ranges["entry"]["min"].astext, Integer) >= min_salary,
                    cast(Career.salary_ranges["mid"]["min"].astext, Integer) >= min_salary,
                )
            )

        if max_salary is not None:
            stmt = stmt.where(
                or_(
                    cast(Career.salary_ranges["entry"]["max"].astext, Integer) <= max_salary,
                    cast(Career.salary_ranges["mid"]["max"].astext, Integer) <= max_salary,
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total_count = total_res.scalar() or 0

        # Stable ordering & pagination
        stmt = stmt.order_by(Career.title.asc(), Career.id.asc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        res = await self.session.execute(stmt)
        careers = list(res.scalars().all())
        return careers, total_count

    async def get_by_id(
        self,
        career_id: UUID,
        allow_drafts: bool = False,
        eager_load: bool = True,
    ) -> Optional[Career]:
        stmt = select(Career).where(Career.id == career_id)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")

        if eager_load:
            stmt = stmt.options(
                selectinload(Career.exams),
                selectinload(Career.colleges),
                selectinload(Career.courses),
                selectinload(Career.certificates),
                selectinload(Career.internships),
                selectinload(Career.related_careers),
            )

        res = await self.session.execute(stmt)
        career = res.scalar_one_or_none()
        if not career:
            return None

        # Filter linked entities if drafts not allowed
        if not allow_drafts and eager_load:
            career.exams = [e for e in career.exams if e.status == "verified"]
            career.colleges = [c for c in career.colleges if c.status == "verified"]
            career.courses = [c for c in career.courses if c.status == "verified"]
            career.certificates = [c for c in career.certificates if c.status == "verified"]
            career.internships = [i for i in career.internships if i.status == "verified"]
            career.related_careers = [r for r in career.related_careers if r.status == "verified"]

        return career

    async def get_by_code(self, code: str, allow_drafts: bool = False) -> Optional[Career]:
        stmt = select(Career).where(Career.code == code)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def search_careers(
        self,
        query: str,
        allow_drafts: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Career], int]:
        clean_q = query.strip()
        if not clean_q:
            return [], 0

        stmt = select(Career)
        if not allow_drafts:
            stmt = stmt.where(Career.status == "verified")

        stmt = stmt.where(
            or_(
                Career.title.ilike(f"%{clean_q}%"),
                Career.cluster.ilike(f"%{clean_q}%"),
                func.array_to_string(Career.aliases, ",").ilike(f"%{clean_q}%"),
            )
        )
        res = await self.session.execute(stmt)
        careers = list(res.scalars().all())

        clean_lower = clean_q.lower()

        def rank_key(c: Career):
            t_lower = c.title.lower()
            if t_lower == clean_lower:
                rank = 0
            elif t_lower.startswith(clean_lower):
                rank = 1
            elif any(clean_lower in str(a).lower() for a in (c.aliases or [])):
                rank = 2
            elif clean_lower in t_lower:
                rank = 3
            else:
                rank = 4
            return (rank, c.title, str(c.id))

        careers.sort(key=rank_key)
        total_count = len(careers)
        offset = (page - 1) * page_size
        return careers[offset : offset + page_size], total_count
