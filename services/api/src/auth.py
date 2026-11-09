"""Caller authentication for the public API.

Two distinct callers exist and neither is allowed to assert its own identity:

* end users  -> a Firebase / Identity Platform ID token, verified by
  ``firebase_admin.auth.verify_id_token``. The uid is taken from the verified
  token only. No header is ever trusted.
* Cloud Tasks -> an OIDC token minted for the queue's service account, verified
  against the service's own audience, plus an allow-list of caller service
  accounts.

The previous implementation trusted an ``X-Firebase-Uid`` header verbatim and,
for bearer tokens, hashed whatever string it was given and used that as the
uid -- so ``Authorization: Bearer hello`` was a valid, stable identity. Nothing
here may reintroduce that behaviour: if a token cannot be verified, the request
is rejected.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import firebase_admin
from fastapi import Header, HTTPException
from firebase_admin import auth as fb_auth
from google.api_core.client_options import ClientOptions
from google.auth.transport import requests as ga_requests
from google.cloud import firestore
from google.oauth2 import id_token as google_id_token

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0484425781")
QUOTA_OPTS = ClientOptions(quota_project_id=PROJECT_ID)

# Requests allowed per uid per rolling minute.
RATE_LIMIT_PER_MINUTE = int(os.environ.get("PM_RATE_LIMIT_PER_MINUTE", "60"))

# Service accounts permitted to call /internal/* via an OIDC token.
_INTERNAL_CALLERS = tuple(
    sa.strip()
    for sa in os.environ.get("PM_INTERNAL_CALLER_SERVICE_ACCOUNTS", "").split(",")
    if sa.strip()
)

# The audience the OIDC token must carry: this service's own base URL.
_SERVICE_BASE_URL = os.environ.get("PM_SERVICE_BASE_URL", "").rstrip("/")

_fb_app: Optional[firebase_admin.App] = None


def _firebase_app() -> firebase_admin.App:
    """Initialise the Firebase Admin SDK once, from Application Default Credentials."""
    global _fb_app
    if _fb_app is None:
        try:
            _fb_app = firebase_admin.get_app()
        except ValueError:
            _fb_app = firebase_admin.initialize_app(options={"projectId": PROJECT_ID})
    return _fb_app


def _db() -> firestore.Client:
    return firestore.Client(project=PROJECT_ID, client_options=QUOTA_OPTS)


def _enforce_rate_limit(uid: str) -> None:
    """Count this uid's requests in the current minute, in Firestore.

    An in-process dict cannot do this: Cloud Run runs many instances, so a
    per-instance counter lets a caller exceed the limit by a factor of the
    instance count, and loses the count entirely on every cold start.
    """
    minute = int(time.time() // 60)
    ref = _db().collection("rateLimits").document(f"{uid}:{minute}")
    db = ref._client

    @firestore.transactional
    def _bump(txn: firestore.Transaction) -> int:
        snap = ref.get(transaction=txn)
        count = (snap.to_dict() or {}).get("count", 0) if snap.exists else 0
        count += 1
        txn.set(ref, {"uid": uid, "minute": minute, "count": count})
        return count

    count = _bump(db.transaction())
    if count > RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded ({RATE_LIMIT_PER_MINUTE} requests/min)",
        )


def verify_caller(authorization: Optional[str] = Header(default=None)) -> str:
    """Return the verified uid of the end user, or raise 401.

    Only a verified Identity Platform ID token is accepted.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token: send 'Authorization: Bearer <Identity Platform ID token>'",
        )
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Empty bearer token")

    try:
        decoded = fb_auth.verify_id_token(token, app=_firebase_app(), check_revoked=True)
    except fb_auth.RevokedIdTokenError:
        raise HTTPException(status_code=401, detail="ID token has been revoked")
    except fb_auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="ID token has expired")
    except (fb_auth.InvalidIdTokenError, fb_auth.CertificateFetchError, ValueError) as exc:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {type(exc).__name__}")

    uid = decoded.get("uid") or decoded.get("sub")
    if not uid:
        raise HTTPException(status_code=401, detail="Verified token carries no uid")

    _enforce_rate_limit(uid)
    return uid


def verify_internal_caller(authorization: Optional[str] = Header(default=None)) -> str:
    """Return the verified service-account email of an internal caller, or raise 403.

    Used for the endpoints Cloud Tasks calls. Requires both
    PM_SERVICE_BASE_URL and PM_INTERNAL_CALLER_SERVICE_ACCOUNTS to be set:
    without them the audience and the caller cannot be checked, so the endpoint
    fails closed rather than accepting an unverified request.
    """
    if not _SERVICE_BASE_URL or not _INTERNAL_CALLERS:
        raise HTTPException(
            status_code=503,
            detail=(
                "Internal endpoints are not configured: set PM_SERVICE_BASE_URL and "
                "PM_INTERNAL_CALLER_SERVICE_ACCOUNTS"
            ),
        )
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing internal OIDC token")

    token = authorization.split(" ", 1)[1].strip()
    try:
        claims = google_id_token.verify_oauth2_token(
            token, ga_requests.Request(), audience=_SERVICE_BASE_URL
        )
    except Exception as exc:
        raise HTTPException(status_code=403, detail=f"Invalid internal OIDC token: {type(exc).__name__}")

    email = claims.get("email", "")
    if not claims.get("email_verified") or email not in _INTERNAL_CALLERS:
        raise HTTPException(status_code=403, detail="Internal caller is not allow-listed")
    return email
