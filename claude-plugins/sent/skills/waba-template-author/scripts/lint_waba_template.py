#!/usr/bin/env python3
"""Lint the JSON body sent to ``POST /v3/templates``.

This validator intentionally accepts the Sent v3 request contract, not Meta's
Cloud API ``components[]`` format. Meta payloads are useful reference material,
but must be labelled and converted before they are sent to Sent.

Exit codes:
    0 - valid template payload (warnings may be printed)
    1 - invalid payload or unreadable/malformed input
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


TOP_LEVEL_FIELDS = {
    "category",
    "language",
    "definition",
    "creation_source",
    "submit_for_review",
    "sandbox",
}
CREATE_UNSUPPORTED_FIELDS = {"name", "channels", "body", "header", "buttons", "components"}
VALID_CATEGORIES = {"UTILITY", "MARKETING", "AUTHENTICATION"}
VALID_BODY_CHANNELS = {"multiChannel", "sms", "whatsapp", "rcs"}
VALID_BUTTON_TYPES = {"QUICK_REPLY", "URL", "VOICE_CALL", "PHONE_NUMBER", "COPY_CODE"}
BUTTON_LIMITS = {
    "QUICK_REPLY": 10,
    "URL": 2,
    "VOICE_CALL": 1,
    "PHONE_NUMBER": 1,
    "COPY_CODE": 1,
}
LANGUAGE_RE = re.compile(r"^[a-z]{2}(?:_[A-Z]{2})?$")
PLACEHOLDER_RE = re.compile(r"\{\{(\d+):(variable|link|media)\}\}")
ANY_PLACEHOLDER_RE = re.compile(r"\{\{[^{}]+\}\}")
PROMO_WARN_PHRASES = (
    "buy now",
    "limited time",
    "special offer",
    "discount",
    "sale",
    "free shipping",
)
PROMO_FAIL_PHRASES = ("click here to purchase",)


class LintResult:
    def __init__(self) -> None:
        self.errors: list[tuple[str, str]] = []
        self.warnings: list[tuple[str, str]] = []

    def error(self, field: str, message: str) -> None:
        self.errors.append((field, message))

    def warn(self, field: str, message: str) -> None:
        self.warnings.append((field, message))

    @property
    def failed(self) -> bool:
        return bool(self.errors)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _reject_unknown_fields(
    value: dict[str, Any], allowed: set[str], field: str, result: LintResult
) -> None:
    for key in sorted(set(value) - allowed):
        result.error(f"{field}.{key}" if field else key, "field is not part of the Sent v3 request contract")


def _check_variable(
    variable: Any,
    field: str,
    expected_kind: str | None,
    result: LintResult,
) -> int | None:
    if not isinstance(variable, dict):
        result.error(field, "variable must be an object")
        return None
    for key in ("id", "name", "type", "props"):
        if key not in variable:
            result.error(f"{field}.{key}", "missing required variable field")
    variable_id = variable.get("id")
    if not isinstance(variable_id, int) or variable_id < 0:
        result.error(f"{field}.id", "must be a non-negative integer")
        variable_id = None
    if not _nonempty(variable.get("name")):
        result.error(f"{field}.name", "must be a non-empty string")
    kind = variable.get("type")
    if kind not in {"variable", "link", "media"}:
        result.error(f"{field}.type", "must be variable, link, or media")
    elif expected_kind is not None and kind != expected_kind:
        result.error(f"{field}.type", f"placeholder declares {expected_kind!r}, but variable declares {kind!r}")
    props = variable.get("props")
    if not isinstance(props, dict):
        result.error(f"{field}.props", "must be an object")
    elif not _nonempty(props.get("sample")):
        result.error(f"{field}.props.sample", "must be a non-empty review and preview sample")
    return variable_id


def _check_content(content: Any, field: str, result: LintResult) -> None:
    if not isinstance(content, dict):
        result.error(field, "must be an object")
        return
    _reject_unknown_fields(content, {"type", "template", "variables"}, field, result)
    template = content.get("template")
    if not _nonempty(template):
        result.error(f"{field}.template", "must be a non-empty string")
        return
    if len(template) > 1024:
        result.error(f"{field}.template", f"body exceeds the 1,024-character limit ({len(template)})")

    placeholders = [(int(match.group(1)), match.group(2)) for match in PLACEHOLDER_RE.finditer(template)]
    malformed = [match.group(0) for match in ANY_PLACEHOLDER_RE.finditer(template) if not PLACEHOLDER_RE.fullmatch(match.group(0))]
    if malformed:
        result.error(
            f"{field}.template",
            "use Sent placeholders such as '{{0:variable}}'; malformed: " + ", ".join(malformed),
        )

    variables = content.get("variables", [])
    if variables is None:
        variables = []
    if not isinstance(variables, list):
        result.error(f"{field}.variables", "must be an array")
        return

    expected = {variable_id: kind for variable_id, kind in placeholders}
    if len(expected) != len({variable_id for variable_id, _ in placeholders}):
        result.error(f"{field}.template", "one placeholder id cannot be reused with different types")
    actual_ids: list[int] = []
    for index, variable in enumerate(variables):
        variable_id = variable.get("id") if isinstance(variable, dict) else None
        checked_id = _check_variable(
            variable,
            f"{field}.variables[{index}]",
            expected.get(variable_id) if isinstance(variable_id, int) else None,
            result,
        )
        if checked_id is not None:
            actual_ids.append(checked_id)
    duplicates = [str(key) for key, count in Counter(actual_ids).items() if count > 1]
    if duplicates:
        result.error(f"{field}.variables", "duplicate variable ids: " + ", ".join(duplicates))
    missing = sorted(set(expected) - set(actual_ids))
    extra = sorted(set(actual_ids) - set(expected))
    if missing:
        result.error(f"{field}.variables", f"missing definitions for placeholder ids {missing}")
    if extra:
        result.error(f"{field}.variables", f"variables without matching placeholders: {extra}")


def _check_header_or_footer(value: Any, field: str, limit: int, result: LintResult) -> None:
    if value is None:
        return
    if not isinstance(value, dict):
        result.error(field, "must be an object or null")
        return
    _reject_unknown_fields(value, {"type", "template", "variables"}, field, result)
    template = value.get("template")
    if not isinstance(template, str):
        result.error(f"{field}.template", "must be a string")
        return
    if len(template) > limit:
        result.error(f"{field}.template", f"exceeds the {limit}-character limit")
    if field.endswith("footer") and (ANY_PLACEHOLDER_RE.search(template) or value.get("variables")):
        result.error(field, "footer variables are not supported")
    elif field.endswith("header"):
        _check_content({"template": template, "variables": value.get("variables", [])}, field, result)


def _check_button(button: Any, index: int, result: LintResult) -> str | None:
    field = f"definition.buttons[{index}]"
    if not isinstance(button, dict):
        result.error(field, "button must be an object")
        return None
    _reject_unknown_fields(button, {"id", "type", "props"}, field, result)
    button_type = button.get("type")
    if button_type not in VALID_BUTTON_TYPES:
        result.error(f"{field}.type", f"must be one of {sorted(VALID_BUTTON_TYPES)}")
        return None
    props = button.get("props")
    if not isinstance(props, dict):
        result.error(f"{field}.props", "must be an object")
        return button_type
    text = props.get("text")
    if not _nonempty(text) or len(text) > 25:
        result.error(f"{field}.props.text", "must be 1–25 characters")
    if button_type == "QUICK_REPLY" and not _nonempty(props.get("quickReplyType")):
        result.error(f"{field}.props.quickReplyType", "is required for QUICK_REPLY")
    elif button_type == "URL":
        if not _nonempty(props.get("urlType")):
            result.error(f"{field}.props.urlType", "is required for URL")
        if not _nonempty(props.get("url")):
            result.error(f"{field}.props.url", "is required for URL")
    elif button_type in {"VOICE_CALL", "PHONE_NUMBER"}:
        if not _nonempty(props.get("countryCode")):
            result.error(f"{field}.props.countryCode", f"is required for {button_type}")
        if not _nonempty(props.get("phoneNumber")):
            result.error(f"{field}.props.phoneNumber", f"is required for {button_type}")
    elif button_type == "COPY_CODE" and not _nonempty(props.get("offerCode")):
        result.error(f"{field}.props.offerCode", "is required for COPY_CODE")
    return button_type


def _check_definition(payload: dict[str, Any], result: LintResult) -> None:
    definition = payload.get("definition")
    if not isinstance(definition, dict):
        result.error("definition", "required and must be an object")
        return
    _reject_unknown_fields(
        definition,
        {"header", "body", "footer", "buttons", "definitionVersion", "authenticationConfig"},
        "definition",
        result,
    )
    body = definition.get("body")
    if not isinstance(body, dict):
        result.error("definition.body", "required and must be an object")
    else:
        _reject_unknown_fields(body, VALID_BODY_CHANNELS, "definition.body", result)
        if body.get("multiChannel") is None:
            result.error("definition.body.multiChannel", "is required as the channel-neutral body")
        for channel, content in body.items():
            if channel in VALID_BODY_CHANNELS and content is not None:
                _check_content(content, f"definition.body.{channel}", result)

    _check_header_or_footer(definition.get("header"), "definition.header", 60, result)
    _check_header_or_footer(definition.get("footer"), "definition.footer", 60, result)

    buttons = definition.get("buttons", [])
    if buttons is None:
        buttons = []
    if not isinstance(buttons, list):
        result.error("definition.buttons", "must be an array or null")
        buttons = []
    elif len(buttons) > 10:
        result.error("definition.buttons", f"at most 10 buttons are allowed, got {len(buttons)}")
    counts = Counter(filter(None, (_check_button(button, index, result) for index, button in enumerate(buttons))))
    for button_type, limit in BUTTON_LIMITS.items():
        if counts[button_type] > limit:
            result.error("definition.buttons", f"{button_type} allows at most {limit}, got {counts[button_type]}")

    authentication = definition.get("authenticationConfig")
    category = payload.get("category")
    if authentication is not None:
        if category != "AUTHENTICATION":
            result.error("definition.authenticationConfig", "is only valid for AUTHENTICATION templates")
        if not isinstance(authentication, dict):
            result.error("definition.authenticationConfig", "must be an object or null")
        else:
            _reject_unknown_fields(
                authentication,
                {"addSecurityRecommendation", "codeExpirationMinutes"},
                "definition.authenticationConfig",
                result,
            )
            recommendation = authentication.get("addSecurityRecommendation")
            if recommendation is not None and not isinstance(recommendation, bool):
                result.error("definition.authenticationConfig.addSecurityRecommendation", "must be boolean")
            expiration = authentication.get("codeExpirationMinutes")
            if expiration is not None and (not isinstance(expiration, int) or not 1 <= expiration <= 90):
                result.error("definition.authenticationConfig.codeExpirationMinutes", "must be an integer from 1 to 90")
    if category == "AUTHENTICATION":
        if authentication is None:
            result.error("definition.authenticationConfig", "is required for AUTHENTICATION templates")
        if any(button_type != "COPY_CODE" for button_type in counts):
            result.error("definition.buttons", "AUTHENTICATION templates may only use COPY_CODE buttons")
        if counts["COPY_CODE"] != 1:
            result.error("definition.buttons", "AUTHENTICATION templates require exactly one COPY_CODE button")


def lint_template(payload: Any) -> LintResult:
    result = LintResult()
    if not isinstance(payload, dict):
        result.error("<root>", "template payload must be a JSON object")
        return result
    if "components" in payload:
        result.error(
            "components",
            "Meta Cloud API components[] is not a Sent payload; convert it to definition before POST /v3/templates",
        )
    for field in sorted(CREATE_UNSUPPORTED_FIELDS & set(payload)):
        result.error(field, "unsupported top-level create field")
    _reject_unknown_fields(payload, TOP_LEVEL_FIELDS, "", result)
    category = payload.get("category")
    if category is not None and category not in VALID_CATEGORIES:
        result.error("category", f"must be one of {sorted(VALID_CATEGORIES)} or null")
    language = payload.get("language")
    if language is not None and (not isinstance(language, str) or not LANGUAGE_RE.fullmatch(language)):
        result.error("language", "must look like en or en_US")
    for field in ("submit_for_review", "sandbox"):
        if field in payload and not isinstance(payload[field], bool):
            result.error(field, "must be boolean")
    _check_definition(payload, result)

    if category == "UTILITY":
        body = payload.get("definition", {}).get("body", {}).get("multiChannel", {})
        text = body.get("template", "") if isinstance(body, dict) else ""
        lowered = text.lower()
        for phrase in PROMO_FAIL_PHRASES:
            if phrase in lowered:
                result.error("definition.body.multiChannel.template", f"UTILITY body contains promotional phrase {phrase!r}")
        for phrase in PROMO_WARN_PHRASES:
            if phrase in lowered:
                result.warn("definition.body.multiChannel.template", f"Meta may reclassify promotional phrase {phrase!r} as MARKETING")
    return result


def _format(prefix: str, entries: list[tuple[str, str]]) -> str:
    return "\n".join(f"{prefix} {field}: {message}" for field, message in entries)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Sent POST /v3/templates request JSON")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"could not read {args.path}: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {args.path}: {exc}", file=sys.stderr)
        return 1
    result = lint_template(payload)
    if result.warnings:
        print(_format("WARN", result.warnings))
    if result.errors:
        print(_format("FAIL", result.errors), file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
