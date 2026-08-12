---
name: version-bump
description: Always bump the patch version (X.X.N) across this repo's version-bearing configs when pushing a fix or feature after working a GitHub issue. Use before every `git push` that closes or advances an issue in aws-idp-saml.
---

# Bumping the version after working an issue

This repo tracks its version in three places that must always agree.
The release workflow (`.github/workflows/release.yml`) enforces this at
tag time by failing the release if `constants.__version__` doesn't match
the git tag — so drift caught late blocks a release; catching it here,
per-issue, keeps it from accumulating.

## The three places, kept in sync

1. `constants.py` — `__version__ = 'X.Y.Z'` (the runtime source of truth;
   this is what the release workflow reads and checks against the tag)
2. `pyproject.toml` — `[project]` block's `version = "X.Y.Z"`
3. `pyproject.toml` — `[tool.poetry]` block's `version = "X.Y.Z"`
   (yes, both blocks exist and both must be updated — `pyproject.toml`
   currently carries a Poetry section alongside the PEP 621 `[project]`
   section; don't edit only one)

All three must show the identical version string. Grep to confirm after
editing:

```bash
grep -n "__version__" constants.py
grep -n "^version" pyproject.toml
```

## When to bump

**Every push that closes or meaningfully advances a GitHub issue** —
bump the patch component before pushing, in the same commit/PR as the
fix, not a separate release commit. `X.Y.Z` → `X.Y.(Z+1)`.

**Skip it** for pure housekeeping with no issue behind it: branch
cleanup, memory/doc-only updates, CI config tweaks unrelated to a
tracked issue, README edits. If in doubt, ask rather than guess.

**Patch-only.** Don't bump the minor or major version, or reset the
patch number — that's a separate, deliberate decision made when actually
cutting a numbered release (see below), not something this per-issue
convention decides.

## After bumping pyproject.toml, regenerate the lockfile

`uv.lock` is gitignored in this repo (never committed), but it still
exists on disk locally and pins the project's own version. Changing
`pyproject.toml`'s version without regenerating it leaves the local
lockfile stale, which surfaces as `uv sync --locked` (or plain `uv
sync` noticing the mismatch) complaining the lockfile needs updating:

```bash
uv lock
```

Cheap, always safe to run after a version bump, and matches what CI
effectively re-derives fresh on every run anyway.

## Relationship to actual releases

This per-issue patch bump is independent of cutting a real, tagged
release. Tagging a version (`git tag X.Y.Z && git push origin X.Y.Z`)
is a separate, deliberate action that publishes a GitHub Release via
the release workflow — see the repo's release process for that. The
per-issue bump just keeps `main`'s version numbers moving forward
incrementally so they're never stale by the time someone does decide to
tag a release.
