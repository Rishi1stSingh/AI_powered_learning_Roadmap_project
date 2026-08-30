"""Run the deterministic offline Phase 3 demonstration."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from statskill.services.skill_gap import analyze_gaps, load_profile, recommend_courses, role_name

profile = load_profile("Demo employee", {"statistical analysis": 55, "python": 45, "mathematics": 60})
code = "15-2041.00"
gaps = analyze_gaps(profile, code)
courses = recommend_courses(gaps)
print(f"Phase 3 demo: {profile.name} -> {role_name(code)}")
print(f"Skills: {len(gaps)} | gaps: {(gaps['gap'] > 0).sum()} | recommendations: {len(courses)}")
print(courses[["course_title", "coverage", "score"]].to_string(index=False))
