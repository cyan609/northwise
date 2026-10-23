#!/usr/bin/env python3
"""Tests for the OpenRouter provider path.

Everything here runs offline: the HTTP call is mocked, so these tests exercise
provider selection, request shape, response parsing, error classification and
the citation/refusal guarantees without touching the network or needing a key.

Run:
    python3 test_openrouter.py
"""
import json
import os
import socket
import unittest
import urllib.error
from unittest.mock import patch

import app

CITATION = "[aeiar-276-2026, Ch.4, p.4-28]"
VALID_ANSWER = "The report recommends temporary noise barriers " + CITATION + "."


class FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload


def openrouter_body(content: str, model: str = "google/gemma-4-26b-a4b-it:free",
                    tokens: int = 12) -> bytes:
    return json.dumps({
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 900, "completion_tokens": tokens},
    }).encode()


class ProviderTestCase(unittest.TestCase):
    """Base: clean provider environment and no leftover cooldown per test."""

    def setUp(self):
        app._clear_cooldown()
        self._env = patch.dict(os.environ, {}, clear=False)
        self._env.start()
        for name in ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "LLM_PROVIDER"):
            os.environ.pop(name, None)

    def tearDown(self):
        self._env.stop()
        app._clear_cooldown()


class ProviderSelectionTest(ProviderTestCase):

    def test_no_key_selects_local_model(self):
        self.assertEqual(app._llm_provider(), "ollama")

    def test_key_selects_openrouter(self):
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        self.assertEqual(app._llm_provider(), "openrouter")

    def test_explicit_provider_beats_key(self):
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        os.environ["LLM_PROVIDER"] = "ollama"
        self.assertEqual(app._llm_provider(), "ollama")

    def test_explicit_openrouter_without_key_still_selected(self):
        # Selection is about intent; the missing key is reported at call time.
        os.environ["LLM_PROVIDER"] = "openrouter"
        self.assertEqual(app._llm_provider(), "openrouter")

    def test_default_model_constant(self):
        self.assertEqual(app._openrouter_model(), "google/gemma-4-26b-a4b-it:free")

    def test_model_override_from_environment(self):
        os.environ["OPENROUTER_MODEL"] = "anthropic/claude-3.5-haiku"
        self.assertEqual(app._openrouter_model(), "anthropic/claude-3.5-haiku")


class MissingKeyTest(ProviderTestCase):

    def test_missing_key_raises_without_any_network_call(self):
        os.environ["LLM_PROVIDER"] = "openrouter"
        calls = []

        def explode(*a, **k):
            calls.append(a)
            raise AssertionError("no network call should happen without a key")

        with patch("urllib.request.urlopen", side_effect=explode):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 100)
        self.assertEqual(calls, [])


class RequestShapeTest(ProviderTestCase):

    def test_headers_body_and_url(self):
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["req"] = req
            captured["timeout"] = timeout
            return FakeResponse(openrouter_body(VALID_ANSWER))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            app._call_model([{"role": "user", "content": "hi"}], 321)

        req = captured["req"]
        self.assertEqual(req.full_url, "https://openrouter.ai/api/v1/chat/completions")
        self.assertEqual(req.get_header("Authorization"), "Bearer test-key-not-real")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        body = json.loads(req.data.decode())
        self.assertEqual(body["model"], "google/gemma-4-26b-a4b-it:free")
        self.assertEqual(body["max_tokens"], 321)
        self.assertFalse(body["stream"])
        self.assertEqual(captured["timeout"], app.OPENROUTER_TIMEOUT)


class ResponseParsingTest(ProviderTestCase):

    def setUp(self):
        super().setUp()
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"

    def test_content_model_and_tokens_are_normalised(self):
        with patch("urllib.request.urlopen",
                   return_value=FakeResponse(openrouter_body("Answer " + CITATION, tokens=77))):
            text, data = app._call_model([{"role": "user", "content": "hi"}], 100)
        self.assertEqual(text, "Answer " + CITATION)
        self.assertEqual(data["_model"], "google/gemma-4-26b-a4b-it:free")
        self.assertEqual(data["_tokens"], 77)
        self.assertEqual(data["_provider"], "openrouter")

    def test_served_model_wins_over_requested_model(self):
        body = openrouter_body("x", model="meta-llama/actual-served-model")
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)):
            _, data = app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertEqual(data["_model"], "meta-llama/actual-served-model")

    def test_malformed_json_is_unavailable(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(b"<html>oops</html>")):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)

    def test_empty_choices_is_unavailable(self):
        body = json.dumps({"choices": []}).encode()
        with patch("urllib.request.urlopen", return_value=FakeResponse(body)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)

    def test_blank_content_is_unavailable(self):
        with patch("urllib.request.urlopen", return_value=FakeResponse(openrouter_body("   "))):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)


class ErrorHandlingTest(ProviderTestCase):

    def setUp(self):
        super().setUp()
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"

    def _http_error(self, code):
        return urllib.error.HTTPError(
            app.OPENROUTER_URL, code, "error", {}, None)

    def test_401_starts_a_long_cooldown(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(401)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertTrue(app._in_cooldown())

    def test_403_starts_a_long_cooldown(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(403)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertTrue(app._in_cooldown())

    def test_second_call_during_cooldown_makes_no_network_call(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(401)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        calls = []

        def count(*a, **k):
            calls.append(1)
            return FakeResponse(openrouter_body(VALID_ANSWER))

        with patch("urllib.request.urlopen", side_effect=count):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertEqual(calls, [])

    def test_429_starts_a_cooldown(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(429)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertTrue(app._in_cooldown())

    def test_500_does_not_start_a_cooldown(self):
        # A transient upstream error should be retried by the caller, not
        # benched for half a minute.
        with patch("urllib.request.urlopen", side_effect=self._http_error(500)):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)
        self.assertFalse(app._in_cooldown())

    def test_timeout_is_unavailable(self):
        with patch("urllib.request.urlopen", side_effect=socket.timeout("timed out")):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)

    def test_connection_error_is_unavailable(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.URLError("connection refused")):
            with self.assertRaises(app.SynthesisUnavailable):
                app._call_model([{"role": "user", "content": "hi"}], 10)

    def test_error_messages_never_contain_the_key(self):
        with patch("urllib.request.urlopen", side_effect=self._http_error(500)):
            try:
                app._call_model([{"role": "user", "content": "hi"}], 10)
            except app.SynthesisUnavailable as exc:
                self.assertNotIn("test-key-not-real", str(exc))
                self.assertNotIn("test-key-not-real", repr(exc))


class EndToEndTest(ProviderTestCase):
    """Through ask(): retrieval, validation and refusal must be unaffected."""

    def setUp(self):
        super().setUp()
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"

    def test_model_answer_is_used_and_attributed_to_openrouter(self):
        with patch("urllib.request.urlopen",
                   return_value=FakeResponse(openrouter_body(VALID_ANSWER, tokens=64))):
            r = app.ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertIsNotNone(r["synthesis"])
        self.assertEqual(r["synthesis"]["model"], "google/gemma-4-26b-a4b-it:free")
        self.assertNotEqual(r["synthesis"]["model"], app.OLLAMA_MODEL)
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_invented_citation_is_rejected_and_falls_back(self):
        invented = "The project will build a 40-storey tower [aeiar-276-2026, Ch.99, p.99-99]."
        with patch("urllib.request.urlopen",
                   return_value=FakeResponse(openrouter_body(invented))):
            r = app.ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["synthesis"]["model"], "evidence-summary")
        self.assertNotIn("40-storey tower", r["synthesis"]["answer"])

    def test_api_failure_degrades_to_evidence_summary(self):
        with patch("urllib.request.urlopen",
                   side_effect=urllib.error.HTTPError(app.OPENROUTER_URL, 503, "down", {}, None)):
            r = app.ask("noise barrier", "en")
        self.assertFalse(r["refused"])
        self.assertEqual(r["synthesis"]["model"], "evidence-summary")
        self.assertGreaterEqual(len(r["evidence"]), 1)

    def test_insufficient_evidence_keeps_the_exact_refusal(self):
        with patch("urllib.request.urlopen") as call:
            r = app.ask("What is the capital of France?", "en")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], "Sorry, I cannot answer this question")
        self.assertEqual(r["evidence"], [])
        call.assert_not_called()

    def test_chinese_refusal_is_preserved(self):
        r = app.ask("股票市場走勢", "zh-Hant")
        self.assertTrue(r["refused"])
        self.assertEqual(r["message"], "抱歉，我無法回答此問題。")


class HealthTest(ProviderTestCase):

    def test_health_payload_shape(self):
        payload = app._health_payload()
        self.assertIn(payload["status"], ("ok", "degraded"))
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["provider"], "ollama")
        self.assertGreater(payload["reports"], 0)
        self.assertGreater(payload["page_files"], 0)
        self.assertTrue(payload["static"])
        self.assertTrue(payload["registry"])

    def test_health_reports_openrouter_without_leaking_the_key(self):
        os.environ["LLM_PROVIDER"] = "openrouter"
        os.environ["OPENROUTER_API_KEY"] = "test-key-not-real"
        payload = app._health_payload()
        self.assertEqual(payload["provider"], "openrouter")
        self.assertTrue(payload["provider_ready"])
        self.assertNotIn("test-key-not-real", json.dumps(payload))

    def test_health_flags_missing_key(self):
        os.environ["LLM_PROVIDER"] = "openrouter"
        payload = app._health_payload()
        self.assertFalse(payload["provider_ready"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
