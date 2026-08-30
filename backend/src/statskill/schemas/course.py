from pydantic import BaseModel
class CourseView(BaseModel):
    course_id: str
    title: str
