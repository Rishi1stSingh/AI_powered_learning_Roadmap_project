"""Verify PostgreSQL import counts and uniqueness after loading."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from statskill.core.database import SessionLocal, Skill, Role, Course, RoleSkill, CourseSkill, SkillAlias

def main():
    with SessionLocal() as s:
        counts = {name: s.query(model).count() for name, model in {
            "skills": Skill, "roles": Role, "courses": Course,
            "role_skills": RoleSkill, "course_skills": CourseSkill,
            "skill_aliases": SkillAlias}.items()}
        print(counts)
        assert counts["skills"] > 0 and counts["roles"] > 0 and counts["courses"] > 0
        assert counts["role_skills"] > 0 and counts["course_skills"] > 0
        print("PostgreSQL verification passed.")
if __name__ == "__main__": main()
