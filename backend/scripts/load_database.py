"""Idempotently load Phase 2 processed CSVs into PostgreSQL."""
from pathlib import Path
import sys
import pandas as pd
from sqlalchemy import select, delete
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from statskill.core.database import SessionLocal, Skill, Role, Course, RoleSkill, CourseSkill, SkillAlias
from statskill.utils.paths import PROCESSED_DIR

def upsert(session, model, key, values):
    obj = session.get(model, key)
    if obj is None: obj = model(**values); session.add(obj)
    else:
        for field, value in values.items(): setattr(obj, field, value)
    return obj

def main():
    p = PROCESSED_DIR
    taxonomy = pd.read_csv(p / "unified_taxonomy.csv")
    roles = pd.read_csv(p / "mvp_roles.csv")
    courses = pd.read_csv(p.parent / "processed_course_catalog_cleaned.csv")
    role_skills = pd.read_csv(p / "role_skills.csv")
    course_skills = pd.read_csv(p / "course_skills.csv")
    aliases = pd.read_csv(p / "skill_aliases.csv")
    with SessionLocal() as s:
        for _, r in taxonomy.iterrows(): upsert(s, Skill, str(r.skill_id), {"id": str(r.skill_id), "name": str(r.skill_name), "skill_type": str(r.skill_type), "category": str(r.category), "source": str(r.source)})
        for _, r in roles.iterrows(): upsert(s, Role, str(r.onet_code), {"onet_code": str(r.onet_code), "title": str(r.role_title), "description": str(r.role_description), "is_showcase": bool(r.is_showcase_role)})
        for _, r in courses.iterrows(): upsert(s, Course, str(r.course_id), {"course_id": str(r.course_id), "title": str(r.course_title), "domain": str(r.domain), "institution": str(r.institution), "difficulty_level": str(r.difficulty_level), "duration": str(r.duration), "rating": float(r.rating), "reviews": int(r.reviews)})
        s.flush()
        desired_role_keys = {(str(r.onet_code), str(r.skill_id)) for _, r in role_skills.iterrows()}
        for obj in s.scalars(select(RoleSkill).where(RoleSkill.role_code.in_(roles.onet_code.astype(str).tolist()))).all():
            if (obj.role_code, obj.skill_id) not in desired_role_keys: s.delete(obj)
        desired_course_keys = {(str(r.course_id), str(r.skill_id)) for _, r in course_skills[course_skills.mapped.astype(bool)].iterrows()}
        for obj in s.scalars(select(CourseSkill)).all():
            if (obj.course_id, obj.skill_id) not in desired_course_keys: s.delete(obj)
        for _, r in role_skills.iterrows():
            obj = s.scalar(select(RoleSkill).where(RoleSkill.role_code == str(r.onet_code), RoleSkill.skill_id == str(r.skill_id)))
            values = {"role_code": str(r.onet_code), "skill_id": str(r.skill_id), "required_level": int(r.required_level), "importance": int(r.importance), "source": str(r.source), "confidence": str(r.confidence)}
            if obj is None: s.add(RoleSkill(**values))
            else:
                for k,v in values.items(): setattr(obj,k,v)
        for _, r in course_skills[course_skills.mapped.astype(bool)].iterrows():
            obj = s.scalar(select(CourseSkill).where(CourseSkill.course_id == str(r.course_id), CourseSkill.skill_id == str(r.skill_id)))
            values = {"course_id": str(r.course_id), "skill_id": str(r.skill_id), "raw_skill": str(r.raw_skill), "mapped": True}
            if obj is None: s.add(CourseSkill(**values))
        for _, r in aliases.iterrows():
            upsert(s, SkillAlias, str(r.alias), {"alias": str(r.alias), "skill_id": str(r.canonical_skill_id) if str(r.canonical_skill_id) else None, "match_method": str(r.match_method)})
        s.commit()
        print(f"loaded skills={s.query(Skill).count()} roles={s.query(Role).count()} courses={s.query(Course).count()} role_skills={s.query(RoleSkill).count()} course_skills={s.query(CourseSkill).count()} aliases={s.query(SkillAlias).count()}")
if __name__ == "__main__": main()
