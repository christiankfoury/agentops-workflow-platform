from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.http_tool import HTTPDestination

ALIAS = r"^[a-zA-Z][a-zA-Z0-9_.-]{0,99}$"
Operation = Literal["read_issues", "create_issue"]


class GitHubOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    repository: str = Field(pattern=ALIAS)
    operation: Operation


class GitHubRepository(BaseModel):
    model_config = ConfigDict(extra="forbid")
    owner: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9-]{0,38}$")
    repo: str = Field(pattern=r"^[a-zA-Z0-9_.-]{1,100}$")
    credential_alias: str = Field(pattern=ALIAS)
    actor_id: int | None = Field(default=None, gt=0, strict=True)
    operations: set[Operation] = Field(default_factory=lambda: {"read_issues"}, min_length=1)
    origin: str = "https://api.github.com"
    allow_plain_http: bool = False
    allowed_private_cidrs: list[str] = Field(default_factory=list, max_length=20)
    max_response_bytes: int = Field(default=128000, ge=1024, le=128000)
    max_pages: int = Field(default=10, ge=1, le=20)

    def transport(self):
        return HTTPDestination(
            origin=self.origin,
            methods={"GET", "POST"},
            credential_alias=self.credential_alias,
            allow_plain_http=self.allow_plain_http,
            allowed_private_cidrs=self.allowed_private_cidrs,
            max_response_bytes=self.max_response_bytes,
        )

    @model_validator(mode="after")
    def valid_repository(self):
        if self.repo in {".", ".."} or (
            "create_issue" in self.operations
            and (self.actor_id is None or "read_issues" not in self.operations)
        ):
            raise ValueError(
                "Issue creation requires a repository, author ID and reconciliation reads"
            )
        self.origin = self.transport().origin
        return self


class ReadIssues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: Literal["open", "closed", "all"] = "open"
    page: int = Field(default=1, ge=1, le=20, strict=True)
    per_page: int = Field(default=10, ge=1, le=100, strict=True)


class CreateIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=20000)

    @model_validator(mode="after")
    def valid_content(self):
        if not self.title.strip() or "<!-- agentops:" in self.body:
            raise ValueError("Issue contents are invalid")
        return self
