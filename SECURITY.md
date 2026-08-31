# Security Policy

## Supported Version

Security fixes are applied to the latest commit on `main`. Older commits and
local forks are not maintained as supported releases.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting flow from the repository's **Security** tab. If private
reporting is unavailable, contact the maintainer through the GitHub profile and
request a private channel before sharing technical details.

Include the affected route or component, reproduction steps, impact, and any
suggested mitigation. Please avoid accessing data that does not belong to you.

## Deployment Scope

The included Docker Compose configuration is for local development only. It uses
local credentials, binds services to loopback, and disables API authentication by
default for a frictionless demo. Public deployments must provide external secret
management, TLS, a private database, API authentication, rate limiting, and
appropriate network controls.

## Automated Checks

Continuous integration runs application tests, linting, typechecking, production
builds, and dependency audits for Python and JavaScript changes.
