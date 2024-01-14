from pydantic import BaseModel
import datetime
from typing import Literal, Union


class Job(BaseModel):
    type: Literal["Volcano"]
    name: str
    namespace: str
    state: str
    age: Union[datetime.datetime, str]
