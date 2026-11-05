"""Host identity evidence stays distinct from the legacy requested-model fallback."""
from __future__ import annotations

import json

import pytest

from secondsignal_harness import AdapterReply, FakeAdapter
from secondsignal_harness import adapters as adapter_module
from secondsignal_harness.spec import adapter_identity_adapter_reply


@pytest.mark.parametrize("family", ["messages", "chat_completions"])
@pytest.mark.parametrize("identity_fields, legacy_identity, reported", [
    ({}, "requested-alias", False),
    ({"model": None}, "requested-alias", False),
    ({"model": ""}, "requested-alias", False),
    ({"model": "   "}, "   ", False),
    ({"model": 7}, "7", False),
    ({"model": "host-revision"}, "host-revision", True),
])
def test_stubbed_host_response_preserves_legacy_value_and_marks_evidence(
    monkeypatch, family, identity_fields, legacy_identity, reported,
):
    # No environment key is read and the transport is entirely local data.
    monkeypatch.setattr(adapter_module, "_key_from_env", lambda variable: "")
    calls = []

    def transport(url, headers, body):
        calls.append(json.loads(body))
        response = {**identity_fields, "usage": {"output_tokens": 4}}
        if family == "messages":
            response["content"] = [{"type": "text", "text": "A local fixture reply."}]
        else:
            response["choices"] = [{"message": {"content": "A local fixture reply."}}]
        return 200, json.dumps(response).encode("utf-8")

    if family == "messages":
        adapter = adapter_module.AnthropicAdapter("requested-alias", transport=transport)
    else:
        adapter = adapter_module.OpenAICompatibleAdapter(
            "requested-alias", url="https://unused.invalid/completions",
            key_variable="UNUSED_OFFLINE_VARIABLE", transport=transport,
        )
    reply = adapter.complete("fixture system", [{"role": "user", "content": "fixture"}], max_tokens=9)
    assert len(calls) == 1 and calls[0]["model"] == "requested-alias"
    assert reply.text == "A local fixture reply."
    assert reply.model_id == legacy_identity
    assert reply.model_id_reported is reported
    assert reply.usage == {"output_tokens": 4}
    assert adapter_identity_adapter_reply(reply) == {
        "model_id": "host-revision" if reported else None, "model_version": None,
    }


def test_fake_and_existing_positional_replies_default_to_reported_identity():
    # Adding the flag after all old fields preserves their positional meaning.
    existing = AdapterReply("text", "host-id", {"tokens": 2}, "host-version")
    assert existing.model_id_reported is True
    assert adapter_identity_adapter_reply(existing) == {
        "model_id": "host-id", "model_version": "host-version",
    }
    fake = FakeAdapter(model_id="fake-reported-model")
    reply = fake.complete("system", [{"role": "user", "content": "fixture"}], max_tokens=9)
    assert reply.model_id_reported is True
    assert adapter_identity_adapter_reply(reply) == {"model_id": "fake-reported-model", "model_version": "1"}
