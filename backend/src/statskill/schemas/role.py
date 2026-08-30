from pydantic import BaseModel
class RoleView(BaseModel):
    onet_code: str
    title: str
