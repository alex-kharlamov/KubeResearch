from pydantic import BaseModel
import datetime
from typing import Literal


class Job(BaseModel):
    type: Literal["Volcano"]
    name: str
    namespace: str
    state: str
    age: datetime.datetime
