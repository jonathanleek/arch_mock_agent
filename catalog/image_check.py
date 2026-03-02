"""Lightweight Docker image validation via the Registry v2 HTTP API.

Uses stdlib ``urllib`` so there are no extra dependencies.  Avoids
``docker manifest inspect`` which counts against Docker Hub's
unauthenticated pull rate-limit and requires the Docker CLI.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Tuple


# Docker Hub uses a two-step flow: obtain a bearer token from
# auth.docker.io, then query registry-1.docker.io.
_DOCKER_HUB_AUTH = "https://auth.docker.io/token"
_DOCKER_HUB_REGISTRY = "https://registry-1.docker.io"

# Accept header that covers OCI and Docker manifest schemas.
_MANIFEST_ACCEPT = (
    "application/vnd.docker.distribution.manifest.v2+json, "
    "application/vnd.docker.distribution.manifest.list.v2+json, "
    "application/vnd.oci.image.manifest.v1+json, "
    "application/vnd.oci.image.index.v1+json"
)

_TIMEOUT = 10  # seconds – keeps the tool snappy


def _parse_image(image: str) -> Tuple[str, str, str]:
    """Split *image* into ``(registry, repository, tag)``.

    Docker Hub images may omit the registry and the ``library/`` prefix.
    """
    # Separate tag / digest
    if "@" in image:
        repo_part, tag = image.rsplit("@", 1)
    elif ":" in image.split("/")[-1]:
        repo_part, tag = image.rsplit(":", 1)
    else:
        repo_part, tag = image, "latest"

    parts = repo_part.split("/")

    # Heuristic: if the first segment contains a dot or colon it's a
    # registry hostname (e.g. "mcr.microsoft.com", "ghcr.io").
    if len(parts) >= 2 and ("." in parts[0] or ":" in parts[0]):
        registry = parts[0]
        repository = "/".join(parts[1:])
    else:
        # Docker Hub
        registry = "docker.io"
        repository = "/".join(parts)

    # Docker Hub official images live under "library/"
    if registry == "docker.io" and "/" not in repository:
        repository = f"library/{repository}"

    return registry, repository, tag


def _check_docker_hub(repository: str, tag: str) -> bool:
    """Check Docker Hub using the v2 token + manifest HEAD flow."""
    # 1. Get a short-lived bearer token (anonymous, no rate-limit hit).
    token_url = (
        f"{_DOCKER_HUB_AUTH}"
        f"?service=registry.docker.io"
        f"&scope=repository:{repository}:pull"
    )
    try:
        with urllib.request.urlopen(token_url, timeout=_TIMEOUT) as resp:
            token = json.loads(resp.read())["token"]
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return False

    # 2. HEAD the manifest endpoint.
    manifest_url = f"{_DOCKER_HUB_REGISTRY}/v2/{repository}/manifests/{tag}"
    req = urllib.request.Request(
        manifest_url,
        method="HEAD",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": _MANIFEST_ACCEPT,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status == 200
    except urllib.error.HTTPError:
        return False
    except urllib.error.URLError:
        return False


def _check_generic_registry(registry: str, repository: str, tag: str) -> bool:
    """Best-effort check for non-Docker-Hub registries.

    Many registries (ghcr.io, MCR, quay.io, etc.) support anonymous pulls
    and return a ``Www-Authenticate`` header with the token endpoint when
    an unauthenticated request is made.  We follow that challenge.
    """
    base = f"https://{registry}"
    manifest_url = f"{base}/v2/{repository}/manifests/{tag}"

    # First try: unauthenticated HEAD — some registries allow it.
    head_req = urllib.request.Request(
        manifest_url,
        method="HEAD",
        headers={"Accept": _MANIFEST_ACCEPT},
    )
    try:
        with urllib.request.urlopen(head_req, timeout=_TIMEOUT) as resp:
            return resp.status == 200
    except urllib.error.HTTPError as exc:
        if exc.code != 401:
            return False
        # Try to extract bearer realm from Www-Authenticate.
        www_auth = exc.headers.get("Www-Authenticate", "")
    except urllib.error.URLError:
        return False

    # Parse the bearer challenge.
    if not www_auth.lower().startswith("bearer "):
        return False

    params: dict[str, str] = {}
    for part in www_auth[7:].split(","):
        key, _, val = part.strip().partition("=")
        params[key.strip()] = val.strip().strip('"')

    realm = params.get("realm", "")
    if not realm:
        return False

    # Build token request.
    token_url = realm
    qs_parts = []
    if "service" in params:
        qs_parts.append(f"service={urllib.request.quote(params['service'])}")
    qs_parts.append(f"scope=repository:{repository}:pull")
    token_url = f"{token_url}?{'&'.join(qs_parts)}"

    try:
        with urllib.request.urlopen(token_url, timeout=_TIMEOUT) as resp:
            body = json.loads(resp.read())
            token = body.get("token") or body.get("access_token", "")
    except (urllib.error.URLError, KeyError, json.JSONDecodeError):
        return False

    if not token:
        return False

    # Retry the manifest HEAD with the token.
    auth_req = urllib.request.Request(
        manifest_url,
        method="HEAD",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": _MANIFEST_ACCEPT,
        },
    )
    try:
        with urllib.request.urlopen(auth_req, timeout=_TIMEOUT) as resp:
            return resp.status == 200
    except (urllib.error.HTTPError, urllib.error.URLError):
        return False


def check_image_exists(image: str) -> bool:
    """Return *True* if *image* exists on its registry, *False* otherwise.

    Uses the Docker Registry v2 HTTP API directly — no Docker CLI needed,
    and no pull rate-limit hit.  A 10-second per-request timeout prevents
    network issues from blocking the tool.
    """
    registry, repository, tag = _parse_image(image)

    if registry == "docker.io":
        return _check_docker_hub(repository, tag)
    return _check_generic_registry(registry, repository, tag)
