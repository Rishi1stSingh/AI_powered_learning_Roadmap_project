"""Small typed client for the existing StatSkill HTTP API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class ApiError(RuntimeError):
    """An API request failed or returned an invalid response."""


class StatSkillApi:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = httpx.request(method, f"{self.base_url}{path}", timeout=30, **kwargs)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json().get("detail", detail)
            except ValueError:
                pass
            raise ApiError(f"{exc.response.status_code}: {detail}") from exc
        except httpx.RequestError as exc:
            raise ApiError(f"Could not reach the API at {self.base_url}.") from exc
        try:
            return response.json()
        except ValueError as exc:
            raise ApiError("The API returned an invalid JSON response.") from exc

    def health(self) -> dict[str, Any]:
        return self.request("GET", "/health")

    def create_user(self, name: str, email: str | None) -> dict[str, Any]:
        return self.request("POST", "/users", json={"name": name, "email": email or None})

    def skills(self) -> list[dict[str, Any]]:
        return self.request("GET", "/skills")

    def roles(self) -> list[dict[str, Any]]:
        return self.request("GET", "/roles")

    def courses(self, limit: int = 100) -> list[dict[str, Any]]:
        return self.request("GET", "/courses", params={"limit": limit})

    def course(self, course_id: str) -> dict[str, Any]:
        return self.request("GET", f"/courses/{course_id}")

    def module(self, course_id: str, module_id: str) -> dict[str, Any]:
        return self.request("GET", f"/courses/{course_id}/modules/{module_id}")

    def save_skills(self, user_id: int, skills: list[dict[str, Any]]) -> dict[str, Any]:
        return self.request("PUT", f"/users/{user_id}/skills", json=skills)

    def gaps(self, user_id: int, role_code: str) -> list[dict[str, Any]]:
        return self.request("GET", f"/users/{user_id}/gaps/{role_code}")

    def recommendations(self, user_id: int, role_code: str) -> dict[str, Any]:
        return self.request("GET", f"/users/{user_id}/next-recommendations/{role_code}")

    def enroll(self, user_id: int, course_id: str) -> dict[str, Any]:
        return self.request("POST", f"/users/{user_id}/courses/{course_id}/enrollment")

    def progress(self, user_id: int, course_id: str) -> dict[str, Any]:
        return self.request("GET", f"/users/{user_id}/courses/{course_id}/progress")

    def complete_lesson(
        self, user_id: int, course_id: str, module_id: str, lesson_id: str
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/users/{user_id}/courses/{course_id}/lessons/{lesson_id}/complete",
            params={"module_id": module_id},
        )

    def quiz(
        self, user_id: int, course_id: str, module_id: str, difficulty: str = "intermediate"
    ) -> dict[str, Any]:
        return self.request(
            "GET",
            f"/users/{user_id}/courses/{course_id}/modules/{module_id}/quiz",
            params={"difficulty": difficulty},
        )

    def submit_quiz(
        self,
        user_id: int,
        course_id: str,
        module_id: str,
        attempt_id: int,
        answers: list[int],
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/users/{user_id}/courses/{course_id}/modules/{module_id}/assessment",
            json={"attempt_id": attempt_id, "answers": answers},
        )

    def assessment_history(
        self, user_id: int, course_id: str, module_id: str
    ) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            f"/users/{user_id}/courses/{course_id}/modules/{module_id}/assessments",
        )

    def final_quiz(self, user_id: int, course_id: str) -> dict[str, Any]:
        return self.request("GET", f"/users/{user_id}/courses/{course_id}/final-assessment")

    def submit_final(
        self, user_id: int, course_id: str, answers: list[int]
    ) -> dict[str, Any]:
        return self.request(
            "POST",
            f"/users/{user_id}/courses/{course_id}/final-assessment",
            json={"answers": answers},
        )
