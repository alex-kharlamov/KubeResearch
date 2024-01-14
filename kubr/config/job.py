from pydantic import BaseModel
import datetime


class Job(BaseModel):
    name: str
    namespace: str
    state: str
    age: datetime.datetime
