from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

# "link" = this detail points at one record of another type (a many-to-one link, or "foreign key").
# Example: a student's classroom_id links to one classroom.
FieldType = Literal["str", "int", "float", "bool", "datetime", "link"]


class FieldSpec(BaseModel):
    name: str
    type: FieldType
    required: bool = True
    default: str | None = None
    description: str = ""
    auto: bool = False
    links_to: str | None = None  # only for type "link": the singular name of the other record type


class Resource(BaseModel):
    """One type of record, e.g. student / students, with its details."""

    name: str  # singular, snake_case: student
    plural: str  # students (also the table name and the URL: /students)
    description: str = ""
    fields: list[FieldSpec] = Field(min_length=1)

    @property
    def class_name(self) -> str:
        return "".join(part.capitalize() for part in self.name.split("_"))

    @property
    def user_fields(self) -> list[FieldSpec]:
        """Details a person fills in (links included)."""
        return [f for f in self.fields if not f.auto]

    @property
    def auto_fields(self) -> list[FieldSpec]:
        return [f for f in self.fields if f.auto]

    @property
    def link_fields(self) -> list[FieldSpec]:
        return [f for f in self.fields if f.type == "link"]

    @property
    def value_fields(self) -> list[FieldSpec]:
        """Details a person fills in that are not links (text, numbers, dates, yes/no)."""
        return [f for f in self.user_fields if f.type != "link"]


class Analysis(BaseModel):
    """The whole design: one or more linked record types."""

    title: str
    description: str
    resources: list[Resource] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _upgrade_single_record_shape(cls, data: Any) -> Any:
        # Designs saved before multi-record support had resource_name / resource_plural / fields
        # at the top. Turn them into one resource, so old sessions and seed examples still load.
        if isinstance(data, dict) and "resources" not in data and "resource_name" in data:
            data = dict(data)
            data["resources"] = [
                {
                    "name": data.pop("resource_name"),
                    "plural": data.pop("resource_plural"),
                    "description": data.get("description", ""),
                    "fields": data.pop("fields", []),
                }
            ]
        return data

    def resource(self, name: str) -> Resource | None:
        return next((r for r in self.resources if r.name == name), None)

    def children_of(self, name: str) -> list[tuple[Resource, FieldSpec]]:
        """Every (record type, link detail) that points at `name`: used to stop deleting a record still in use."""
        return [(r, f) for r in self.resources for f in r.link_fields if f.links_to == name]

    def in_creation_order(self) -> list[Resource]:
        """Record types ordered so each comes after the ones it links to (classrooms before students).
        If the links go in a circle, the leftovers are added at the end (the validator reports the circle)."""
        ordered: list[Resource] = []
        remaining = list(self.resources)
        while remaining:
            ready = [r for r in remaining if all(f.links_to in {o.name for o in ordered} for f in r.link_fields)]
            if not ready:
                return ordered + remaining
            for resource in ready:
                ordered.append(resource)
                remaining.remove(resource)
        return ordered


Verdict = Literal["clear", "vague", "reducible", "unsupported", "disallowed"]
QuestionKind = Literal["single_choice", "multi_choice", "yes_no", "short_text", "editable_list"]


class NotIncludedItem(BaseModel):
    category: str = "other"
    text: str


class Question(BaseModel):
    id: str
    text: str
    kind: QuestionKind = "single_choice"
    options: list[str] = []
    allow_other: bool = True
    default: Any = None
    why: str = ""


class Understanding(BaseModel):
    verdict: Verdict
    message: str
    blueprint: Analysis | None = None
    not_included: list[NotIncludedItem] = []
    questions: list[Question] = []
    alternative: str | None = None
    # Steps 4 and 5, shown to the person so the help is never hidden:
    memories_used: list[str] = []  # facts from earlier projects that were given to the model
    examples_used: list[str] = []  # titles of similar approved designs that were given to the model


class SessionCreate(BaseModel):
    requirement: str = Field(min_length=10, max_length=2000)


class AnswersRequest(BaseModel):
    answers: dict[str, Any] = {}
    skip: bool = False


class SessionPublic(BaseModel):
    id: str
    requirement: str
    status: str
    understanding: Understanding
    answers: dict[str, Any] = {}
    job_id: str | None = None


class Credentials(BaseModel):
    """Sign-up and log-in body. 8 to 128 characters: long enough to be safe, short enough
    that nobody can send a huge password to make scrypt slow on purpose."""

    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class UserPublic(BaseModel):
    """What the browser may see about an account (never the password hash)."""

    id: int
    email: str
    role: str


class ProjectSummary(BaseModel):
    """One row in the sidebar. status uses the same words as the frontend's status pill."""

    id: str
    name: str
    status: Literal["waiting", "working", "ready", "failed", "stopped"]
    created_at: str


class MemoryPublic(BaseModel):
    """Step 4: one remembered fact, as the person sees it in "What I remember"."""

    id: int
    fact: str
    created_at: str


class LoginResponse(BaseModel):
    token: str
    user: UserPublic


class GenerateRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=2000)


class GenerateResponse(BaseModel):
    job_id: str


class JobPublic(BaseModel):
    id: str
    status: str
    stage: str
    error: str | None = None
    title: str | None = None
    files: list[str] = []
    latency_s: float | None = None
    metrics: dict[str, Any] = {}
    # The build timeline (kind: Thinking/Doing/Result, text, state: done/current/failed, optional output)
    steps: list[dict[str, Any]] = []
    # The generated project's own tests: name, passed, message
    tests: list[dict[str, Any]] = []
