from dataclasses import dataclass
from enum import Enum


class Status(Enum):
    OK = "ok"
    WARN = "warn"
    FAIL = "fail"


class Severity(Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str
    severity: Severity = Severity.LOW
    why_it_matters: str = ""
    recommendation: str = ""
    score_penalty: int = 0
