"""Configured issue operations; ambiguous creation is reconciled, never replayed."""

import hashlib
import hmac
import json
from email.utils import parsedate_to_datetime
from math import isfinite
from time import monotonic

from pydantic import ValidationError

from src.config import settings
from src.schemas.github_tool import CreateIssue, GitHubOptions, GitHubRepository, ReadIssues
from src.schemas.http_tool import HTTPOptions
from src.schemas.tool import bounded
from src.services import http_tool
from src.services.tool_effects import Reconciliation, ToolAdapter, ToolFailure, digest

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
    "User-Agent": "agentops-workflow-platform",
}


def marker(key, secret):
    return hmac.new(secret.encode(), ("github-issue:" + key).encode(), hashlib.sha256).hexdigest()


def response_error(response, budget):
    status = response.status
    message = ""
    if status == 403:
        # Secondary limits sometimes have only a message. Never retain the body;
        # cap this special-case read separately and keep the HTTP deadline active.
        raw = bytearray()
        while len(raw) < 8192:
            budget.remaining()
            part = response.read1(min(1024, 8192 - len(raw)))
            if not part:
                break
            raw.extend(part)
        try:
            payload = json.loads(raw)
            message = str(payload.get("message", "")).lower() if isinstance(payload, dict) else ""
        except (ValueError, UnicodeError):
            pass
    limited = status == 429 or (
        status == 403
        and (
            response.getheader("Retry-After") is not None
            or response.getheader("X-RateLimit-Remaining") == "0"
            or "rate limit" in message
        )
    )
    if limited:
        delay = 60.0
        try:
            header = response.getheader("Retry-After")
            if header is not None:
                seconds = float(header)
                if not isfinite(seconds) or seconds < 0:
                    raise ValueError("Invalid retry delay")
                delay = max(delay, seconds)
            if response.getheader("X-RateLimit-Remaining") == "0":
                # Use provider Date, not worker wall time, then apply this duration
                # from database time when the effect outcome commits.
                date = parsedate_to_datetime(response.getheader("Date", ""))
                reset = float(response.getheader("X-RateLimit-Reset"))
                if date.tzinfo is None or not isfinite(reset):
                    raise ValueError("Invalid provider reset time")
                delay = max(delay, reset - date.timestamp())
        except (TypeError, ValueError, OverflowError):
            delay = max(delay, 3600.0)
        if not 0 <= delay <= 86400:
            return ToolFailure("tool_denied", uncertain=False)
        return ToolFailure("tool_rate_limit", uncertain=False, retry_after_seconds=delay)
    code = (
        "tool_unavailable"
        if status >= 500 or status in {408, 425}
        else "tool_input_invalid"
        if status in {400, 422}
        else "tool_denied"
    )
    return ToolFailure(code, uncertain=status >= 500 or status in {408, 425})


def issue(value, policy):
    if (
        not isinstance(value, dict)
        or "pull_request" in value
        or type(value.get("number")) is not int
        or value["number"] < 1
        or not isinstance(value.get("title"), str)
        or not (value.get("body") is None or isinstance(value.get("body"), str))
        or value.get("state") not in ("open", "closed")
    ):
        raise ToolFailure("tool_response_invalid")
    return {
        "number": value["number"],
        "title": value["title"],
        "body": value.get("body") or "",
        "state": value["state"],
        "url": f"https://github.com/{policy.owner}/{policy.repo}/issues/{value['number']}",
    }


def adapter(contract, organization_id, credential):
    options = GitHubOptions.model_validate(contract.options)
    raw = settings.github_tool_repositories.get(f"{organization_id}/{options.repository}")
    if raw is None:
        raise ToolFailure("tool_denied", uncertain=False)
    policy = GitHubRepository.model_validate(raw)
    if (
        options.operation not in policy.operations
        or credential is None
        or (credential.source_alias != policy.credential_alias)
    ):
        raise ToolFailure("tool_denied", uncertain=False)
    write = options.operation == "create_issue"
    endpoint = f"/repos/{policy.owner}/{policy.repo}/issues"

    def call(method, arguments, kwargs):
        result = http_tool.request(
            policy.transport(),
            HTTPOptions(destination="github", method=method, path=endpoint),
            arguments=arguments,
            protocol_headers=HEADERS,
            response_error=response_error,
            **{key: value for key, value in kwargs.items() if key not in {"arguments", "options"}},
        )
        if result["status"] != (201 if method == "POST" else 200):
            raise ToolFailure("tool_response_invalid")
        return result["body"]

    def creation(kwargs):
        try:
            content = CreateIssue.model_validate(kwargs["arguments"])
        except ValidationError:
            raise ToolFailure("tool_input_invalid", uncertain=False) from None
        suffix = "\n\n<!-- agentops:" + marker(kwargs["effect_key"], kwargs["secret"]) + " -->"
        return content, suffix, {"title": content.title, "body": content.body + suffix}

    def receipt(value, content, suffix):
        output = issue(value, policy)
        author = value.get("user")
        if (
            output["title"] != content.title
            or output["body"] != content.body + suffix
            or not isinstance(author, dict)
            or type(author.get("id")) is not int
            or author["id"] != policy.actor_id
        ):
            raise ToolFailure("tool_response_invalid")
        output["body"] = content.body
        return {"issue": output}

    def invoke(**kwargs):
        if write:
            content, suffix, arguments = creation(kwargs)
            return receipt(call("POST", arguments, kwargs), content, suffix)
        try:
            arguments = ReadIssues.model_validate(kwargs["arguments"])
            if arguments.page > policy.max_pages:
                raise ValueError("Page limit exceeded")
        except ValueError:
            raise ToolFailure("tool_input_invalid", uncertain=False) from None
        values = call("GET", arguments.model_dump(), kwargs)
        if not isinstance(values, list) or len(values) > arguments.per_page:
            raise ToolFailure("tool_response_invalid")
        more = len(values) == arguments.per_page
        return bounded(
            {
                "issues": [
                    issue(value, policy)
                    for value in values
                    if not (isinstance(value, dict) and "pull_request" in value)
                ],
                "next_page": arguments.page + 1
                if more and arguments.page < policy.max_pages
                else None,
                "page_limit_reached": more and arguments.page == policy.max_pages,
            }
        )

    def reconcile(**kwargs):
        content, suffix, _ = creation(kwargs)
        end, matches = monotonic() + kwargs["timeout_seconds"], {}
        for page in range(1, policy.max_pages + 1):
            kwargs["control"].raise_if_aborted()
            remaining = end - monotonic()
            if remaining <= 0:
                raise ToolFailure("tool_timeout")
            values = call(
                "GET",
                {
                    "state": "all",
                    "sort": "created",
                    "direction": "desc",
                    "per_page": 10,
                    "page": page,
                },
                {**kwargs, "timeout_seconds": remaining},
            )
            if not isinstance(values, list) or len(values) > 10:
                raise ToolFailure("tool_response_invalid")
            for value in values:
                if not isinstance(value, dict):
                    raise ToolFailure("tool_response_invalid")
                if "pull_request" in value or value.get("body") != content.body + suffix:
                    continue
                try:
                    output = receipt(value, content, suffix)
                except ToolFailure:
                    continue
                matches[output["issue"]["number"]] = output
            if len(values) < 10:
                break
        if len(matches) == 1:
            return Reconciliation("succeeded", next(iter(matches.values())))
        # Absence from a bounded/eventually-consistent listing never proves no
        # prior creation. A marker may also have been edited or removed remotely.
        return Reconciliation("unknown")

    return ToolAdapter(
        invoke,
        recovery="reconcile" if write else "none",
        reconcile=reconcile,
        side_effecting=write,
        requires_approval=True,
        correlation_marker=marker if write else None,
        policy_identity=digest(
            {**policy.model_dump(mode="json"), "operations": sorted(policy.operations)}
        ),
    )
