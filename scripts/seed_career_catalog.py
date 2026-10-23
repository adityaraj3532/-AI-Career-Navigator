import asyncio
import json
import logging
from pathlib import Path
from typing import Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.career import (
    Career,
    Certificate,
    College,
    Course,
    Exam,
    Internship,
)

logger = logging.getLogger("scripts.seed_career_catalog")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


async def seed_career_catalog(session: AsyncSession, json_path: Path) -> Dict[str, int]:
    if not json_path.is_file():
        raise FileNotFoundError(f"Catalog seed file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    stats = {
        "exams": 0,
        "colleges": 0,
        "courses": 0,
        "certificates": 0,
        "internships": 0,
        "careers": 0,
    }

    # 1. Exams
    exam_records: Dict[str, Exam] = {}
    for item in data.get("exams", []):
        stmt = select(Exam).where(Exam.code == item["code"])
        res = await session.execute(stmt)
        exam = res.scalar_one_or_none()
        if exam:
            exam.name = item["name"]
            exam.description = item["description"]
            exam.conducting_body = item["conducting_body"]
            exam.exam_level = item["exam_level"]
            exam.registration_url = item.get("registration_url")
            exam.source_url = item["source_url"]
        else:
            exam = Exam(
                code=item["code"],
                name=item["name"],
                description=item["description"],
                conducting_body=item["conducting_body"],
                exam_level=item["exam_level"],
                registration_url=item.get("registration_url"),
                source_url=item["source_url"],
                status=item.get("status", "draft"),
            )
            session.add(exam)
            stats["exams"] += 1
        exam_records[item["code"]] = exam

    # 2. Colleges
    college_records: Dict[str, College] = {}
    for item in data.get("colleges", []):
        stmt = select(College).where(College.name == item["name"])
        res = await session.execute(stmt)
        college = res.scalar_one_or_none()
        if college:
            college.location = item["location"]
            college.official_url = item["official_url"]
            college.source_url = item["source_url"]
        else:
            college = College(
                name=item["name"],
                location=item["location"],
                official_url=item["official_url"],
                source_url=item["source_url"],
                fees=item.get("fees"),
                cutoffs=item.get("cutoffs"),
                nirf_rank=item.get("nirf_rank"),
                status=item.get("status", "draft"),
            )
            session.add(college)
            stats["colleges"] += 1
        college_records[item["name"]] = college

    # 3. Courses
    course_records: Dict[str, Course] = {}
    for item in data.get("courses", []):
        stmt = select(Course).where(Course.code == item["code"])
        res = await session.execute(stmt)
        course = res.scalar_one_or_none()
        if course:
            course.title = item["title"]
            course.degree_level = item["degree_level"]
            course.duration = item["duration"]
            course.description = item["description"]
            course.source_url = item["source_url"]
        else:
            course = Course(
                code=item["code"],
                title=item["title"],
                degree_level=item["degree_level"],
                duration=item["duration"],
                description=item["description"],
                source_url=item["source_url"],
                status=item.get("status", "draft"),
            )
            session.add(course)
            stats["courses"] += 1
        course_records[item["code"]] = course

    # 4. Certificates
    cert_records: Dict[str, Certificate] = {}
    for item in data.get("certificates", []):
        stmt = select(Certificate).where(Certificate.code == item["code"])
        res = await session.execute(stmt)
        cert = res.scalar_one_or_none()
        if cert:
            cert.name = item["name"]
            cert.issuing_organization = item["issuing_organization"]
            cert.description = item["description"]
            cert.url = item.get("url")
            cert.source_url = item["source_url"]
        else:
            cert = Certificate(
                code=item["code"],
                name=item["name"],
                issuing_organization=item["issuing_organization"],
                description=item["description"],
                url=item.get("url"),
                source_url=item["source_url"],
                status=item.get("status", "draft"),
            )
            session.add(cert)
            stats["certificates"] += 1
        cert_records[item["code"]] = cert

    # 5. Internships
    intern_records: Dict[str, Internship] = {}
    for item in data.get("internships", []):
        stmt = select(Internship).where(Internship.code == item["code"])
        res = await session.execute(stmt)
        intern = res.scalar_one_or_none()
        if intern:
            intern.title = item["title"]
            intern.domain = item["domain"]
            intern.stipend_range = item.get("stipend_range")
            intern.duration_months = item.get("duration_months")
            intern.locations = item.get("locations", [])
            intern.description = item["description"]
            intern.source_url = item["source_url"]
        else:
            intern = Internship(
                code=item["code"],
                title=item["title"],
                domain=item["domain"],
                stipend_range=item.get("stipend_range"),
                duration_months=item.get("duration_months"),
                locations=item.get("locations", []),
                description=item["description"],
                source_url=item["source_url"],
                status=item.get("status", "draft"),
            )
            session.add(intern)
            stats["internships"] += 1
        intern_records[item["code"]] = intern

    await session.flush()

    # 6. Careers
    career_records: Dict[str, Career] = {}
    for item in data.get("careers", []):
        stmt = select(Career).where(Career.code == item["code"])
        res = await session.execute(stmt)
        career = res.scalar_one_or_none()

        if career:
            career.title = item["title"]
            career.cluster = item["cluster"]
            career.aliases = item.get("aliases", [])
            career.overview = item["overview"]
            career.description = item.get("description")
            career.day_in_life = item.get("day_in_life")
            career.salary_ranges = item.get("salary_ranges")
            career.demand = item.get("demand", "moderate")
            career.time_to_job_ready_months = item.get("time_to_job_ready_months")
            career.entrance_difficulty = item.get("entrance_difficulty")
            career.required_skills = item.get("required_skills", [])
            career.education_paths = item.get("education_paths", [])
            career.source_url = item["source_url"]
            career.dimension_weights = item["dimension_weights"]
        else:
            career = Career(
                code=item["code"],
                title=item["title"],
                cluster=item["cluster"],
                aliases=item.get("aliases", []),
                overview=item["overview"],
                description=item.get("description"),
                day_in_life=item.get("day_in_life"),
                salary_ranges=item.get("salary_ranges"),
                demand=item.get("demand", "moderate"),
                time_to_job_ready_months=item.get("time_to_job_ready_months"),
                entrance_difficulty=item.get("entrance_difficulty"),
                required_skills=item.get("required_skills", []),
                education_paths=item.get("education_paths", []),
                source_url=item["source_url"],
                dimension_weights=item["dimension_weights"],
                status=item.get("status", "draft"),
            )
            session.add(career)
            stats["careers"] += 1

        career_records[item["code"]] = career

    await session.flush()

    # 7. Associations linking
    for item in data.get("careers", []):
        career = career_records[item["code"]]

        # exams
        linked_exams = [exam_records[c] for c in item.get("exam_codes", []) if c in exam_records]
        career.exams = linked_exams

        # colleges
        linked_colleges = [college_records[c] for c in item.get("college_names", []) if c in college_records]
        career.colleges = linked_colleges

        # courses
        linked_courses = [course_records[c] for c in item.get("course_codes", []) if c in course_records]
        career.courses = linked_courses

        # certificates
        linked_certs = [cert_records[c] for c in item.get("certificate_codes", []) if c in cert_records]
        career.certificates = linked_certs

        # internships
        linked_interns = [intern_records[c] for c in item.get("internship_codes", []) if c in intern_records]
        career.internships = linked_interns

        # related careers (asserting career_id != related_career_id)
        linked_related = [
            career_records[rc]
            for rc in item.get("related_career_codes", [])
            if rc in career_records and career_records[rc].id != career.id
        ]
        career.related_careers = linked_related

    await session.commit()
    logger.info("Career catalog seeded successfully: %s", stats)
    return stats


async def main() -> None:
    seed_file = Path(__file__).resolve().parent.parent / "app" / "data" / "seed" / "career_catalog.json"
    async with async_session_factory() as session:
        await seed_career_catalog(session, seed_file)


if __name__ == "__main__":
    asyncio.run(main())
