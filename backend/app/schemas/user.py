from uuid import UUID
from pydantic import BaseModel


class CurrentUser(BaseModel):
    id: UUID
    username: str
    email: str
    first_name: str
    last_name: str