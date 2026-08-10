#!/usr/bin/env python3
"""Reference implementation and test oracle for Sent v3 webhook signatures.

The signed content is exactly ``{webhook_id}.{timestamp}.{raw_body}``. The key is
the signing secret with its ``whsec_`` prefix removed and the remainder
base64-decoded. The signature header value is ``v1,{base64(hmac_sha256)}``.

Usage
-----
Self-test with synthetic fixtures (no network, no credentials)::

    python3 verify_signature.py --self-test

Verify a captured delivery::

    python3 verify_signature.py --body-file delivery.json \
        --webhook-id 0f8fad5b-d9cb-469f-a165-70867728950e \
        --timestamp 1767225600 \
        --signature 'v1,Base64Signature==' \
        --secret-env SENT_DM_WEBHOOK_SECRET

Sign a synthetic delivery so a local receiver can be exercised::

    python3 verify_signature.py --sign --body-file event.json \
        --webhook-id 0f8fad5b-d9cb-469f-a165-70867728950e \
        --secret-env SENT_DM_WEBHOOK_SECRET

Exit codes: 0 valid, 1 invalid signature, 2 replay window exceeded,
3 usage or configuration error.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time

SECRET_PREFIX = "whsec_"
SIGNATURE_PREFIX = "v1,"
TOLERANCE_SECONDS = 300

EXIT_VALID = 0
EXIT_INVALID = 1
EXIT_REPLAY = 2
EXIT_USAGE = 3


def decode_secret(secret: str) -> bytes:
    """Return the raw HMAC key for a Sent signing secret."""
    if not secret:
        raise ValueError("signing secret is empty")
    material = secret[len(SECRET_PREFIX):] if secret.startswith(SECRET_PREFIX) else secret
    padding = "=" * (-len(material) % 4)
    try:
        return base64.b64decode(material + padding, validate=True)
    except (ValueError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise ValueError(f"signing secret is not valid base64 after the prefix: {exc}") from exc


def signed_content(webhook_id: str, timestamp: str, raw_body: bytes) -> bytes:
    """Build the byte string Sent signs."""
    return f"{webhook_id}.{timestamp}.".encode("utf-8") + raw_body


def compute_signature(secret: str, webhook_id: str, timestamp: str, raw_body: bytes) -> str:
    """Return the full ``v1,...`` header value for a delivery."""
    digest = hmac.new(
        decode_secret(secret),
        signed_content(webhook_id, timestamp, raw_body),
        hashlib.sha256,
    ).digest()
    return SIGNATURE_PREFIX + base64.b64encode(digest).decode("ascii")


def signature_matches(secret: str, webhook_id: str, timestamp: str, raw_body: bytes, header: str) -> bool:
    """Constant-time comparison of a received signature header."""
    expected = compute_signature(secret, webhook_id, timestamp, raw_body)
    return hmac.compare_digest(expected, header.strip())


def timestamp_fresh(timestamp: str, now: int | None = None, tolerance: int = TOLERANCE_SECONDS) -> bool:
    """Return True when the timestamp is inside the replay window."""
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        return False
    reference = int(time.time()) if now is None else now
    return abs(reference - sent_at) <= tolerance


def verify(secret: str, webhook_id: str, timestamp: str, raw_body: bytes, header: str) -> int:
    """Return the process exit code for one delivery."""
    if not timestamp_fresh(timestamp):
        return EXIT_REPLAY
    return EXIT_VALID if signature_matches(secret, webhook_id, timestamp, raw_body, header) else EXIT_INVALID


def _self_test() -> int:
    secret = SECRET_PREFIX + base64.b64encode(b"synthetic-signing-key-0123456789").decode("ascii")
    webhook_id = "0f8fad5b-d9cb-469f-a165-70867728950e"
    now = int(time.time())
    timestamp = str(now)
    body = json.dumps(
        {
            "field": "message",
            "event": "message.delivered",
            "value": {
                "message_id": "8ba7b830-9dad-11d1-80b4-00c04fd430c8",
                "message_status": "DELIVERED",
                "channel": "sms",
                "account_id": "3f1a7c22-5d8e-4b90-91a2-6c4d0e8f7b31",
            },
        },
        separators=(",", ":"),
    ).encode("utf-8")

    failures: list[str] = []
    header = compute_signature(secret, webhook_id, timestamp, body)

    if not header.startswith(SIGNATURE_PREFIX):
        failures.append("signature header must start with 'v1,'")
    if verify(secret, webhook_id, timestamp, body, header) != EXIT_VALID:
        failures.append("a freshly signed delivery must verify")
    if verify(secret, webhook_id, timestamp, body + b" ", header) != EXIT_INVALID:
        failures.append("a mutated body must fail verification")
    if verify(secret, "11111111-2222-3333-4444-555555555555", timestamp, body, header) != EXIT_INVALID:
        failures.append("a different webhook id must fail verification")
    stale = str(now - (TOLERANCE_SECONDS + 60))
    if verify(secret, webhook_id, stale, body, compute_signature(secret, webhook_id, stale, body)) != EXIT_REPLAY:
        failures.append("a stale timestamp must be rejected as a replay")
    if decode_secret(secret) != decode_secret(secret[len(SECRET_PREFIX):]):
        failures.append("prefixed and unprefixed secrets must decode identically")

    reserialized = json.dumps(json.loads(body)).encode("utf-8")
    if reserialized != body and signature_matches(secret, webhook_id, timestamp, reserialized, header):
        failures.append("re-serialized JSON must not verify; raw bytes are required")

    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)
    if failures:
        return EXIT_INVALID
    print("verify_signature self-test passed: 7 checks")
    return EXIT_VALID


def _resolve_secret(args: argparse.Namespace) -> str:
    if args.secret_env:
        secret = os.environ.get(args.secret_env, "")
        if not secret:
            raise ValueError(f"environment variable {args.secret_env} is unset or empty")
        return secret
    raise ValueError("provide --secret-env naming the environment variable that holds the signing secret")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify or sign a Sent v3 webhook delivery.")
    parser.add_argument("--self-test", action="store_true", help="run synthetic fixtures and exit")
    parser.add_argument("--sign", action="store_true", help="emit headers for a synthetic signed delivery")
    parser.add_argument("--body-file", help="path to the raw request body captured byte for byte")
    parser.add_argument("--webhook-id", help="value of the x-webhook-id header")
    parser.add_argument("--timestamp", help="value of the x-webhook-timestamp header")
    parser.add_argument("--signature", help="value of the x-webhook-signature header")
    parser.add_argument("--secret-env", help="environment variable holding the whsec_ signing secret")
    parser.add_argument(
        "--skip-replay-check",
        action="store_true",
        help="verify the HMAC only, for forensic replay of an archived delivery",
    )
    args = parser.parse_args(argv)

    if args.self_test:
        return _self_test()

    if not args.body_file or not args.webhook_id:
        parser.error("--body-file and --webhook-id are required unless --self-test is used")

    try:
        raw_body = open(args.body_file, "rb").read()
        secret = _resolve_secret(args)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_USAGE

    if args.sign:
        timestamp = args.timestamp or str(int(time.time()))
        print(f"x-webhook-id: {args.webhook_id}")
        print(f"x-webhook-timestamp: {timestamp}")
        print(f"x-webhook-signature: {compute_signature(secret, args.webhook_id, timestamp, raw_body)}")
        return EXIT_VALID

    if not args.timestamp or not args.signature:
        parser.error("--timestamp and --signature are required when verifying")

    if args.skip_replay_check:
        matched = signature_matches(secret, args.webhook_id, args.timestamp, raw_body, args.signature)
        result = EXIT_VALID if matched else EXIT_INVALID
    else:
        result = verify(secret, args.webhook_id, args.timestamp, raw_body, args.signature)

    print({EXIT_VALID: "valid", EXIT_INVALID: "invalid signature", EXIT_REPLAY: "replay window exceeded"}[result])
    return result


if __name__ == "__main__":
    raise SystemExit(main())
