# Decision Ecosystem — mdm-engine
# Copyright (c) 2026 Mücahit Muzaffer Karafil (MchtMzffr)
# SPDX-License-Identifier: MIT
"""Redaction: no secrets in output."""

from mdm_engine.security.redaction import redact_dict


def test_redact_dict_removes_api_key():
    d = {"api_key": "secret123", "mid": 0.5}
    out = redact_dict(d)
    assert out["api_key"] == "[REDACTED]"
    assert out["mid"] == 0.5


def test_redact_dict_nested():
    d = {"nested": {"authorization": "Bearer x"}, "data": 1}
    out = redact_dict(d)
    assert out["nested"]["authorization"] == "[REDACTED]"
    assert out["data"] == 1
