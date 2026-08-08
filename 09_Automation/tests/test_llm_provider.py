"""LLM provider adapter tests (provider-catalog / model-fetch / llm-adapter /
llm-config + ModelAdapter Protocol extension).

Fail-first per the CC-Switch-inspired requirements: provider presets free the
user from base_url/API format/token caps; API keys live server-side only;
DeepSeek ``content: null + reasoning_content`` is a valid success; Chat and
Responses protocols use different endpoints/bodies/parsers; errors map
accurately; a blank key on edit keeps the saved key.

Network is mocked via ``research_os.llm._http.http_request``; the E2E test
against the real DeepSeek API runs only when ``DEEPSEEK_API_KEY`` is set.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from research_os.llm import llm_adapter, llm_config, model_fetch, provider_catalog
except ModuleNotFoundError as exc:
    raise unittest.SkipTest(
        "install product dependencies to run LLM provider tests"
    ) from exc

ROOT = Path(__file__).resolve().parents[2]


def _http(status: int, payload: object, *, raw: str | None = None) -> mock.Mock:
    body = raw.encode() if raw is not None else json.dumps(payload).encode()
    return mock.Mock(return_value=(status, body))


class ProviderCatalogTests(unittest.TestCase):
    def test_deepseek_preset_fields(self) -> None:
        preset = provider_catalog.get_preset("deepseek")
        self.assertEqual("https://api.deepseek.com", preset.base_url)
        self.assertEqual("openai_chat", preset.api_format)
        self.assertEqual("deepseek-chat", preset.default_model)
        self.assertIn("deepseek-reasoner", preset.recommended_models)
        self.assertTrue(preset.api_key_url.startswith("https://"))
        self.assertGreater(preset.timeout, 0)

    def test_catalog_is_structured_for_future_providers(self) -> None:
        for preset in provider_catalog.PROVIDER_CATALOG:
            for field in (
                "id",
                "name",
                "base_url",
                "api_format",
                "api_key_url",
                "default_params",
                "recommended_models",
                "default_model",
                "timeout",
            ):
                self.assertTrue(getattr(preset, field) is not None, field)
            self.assertIn(preset.api_format, {"openai_chat", "openai_responses"})

    def test_unknown_provider_raises(self) -> None:
        with self.assertRaises(ValueError):
            provider_catalog.get_preset("nonexistent")


class LlmConfigTests(unittest.TestCase):
    def _config(self) -> Path:
        temp = tempfile.mkdtemp()
        return Path(temp) / "llm.local.json"

    def test_save_and_load_roundtrip(self) -> None:
        path = self._config()
        llm_config.save_config(
            path, provider="deepseek", api_key="sk-test123", model="deepseek-chat"
        )
        config = llm_config.load_config(path)
        self.assertEqual("deepseek", config["provider"])
        self.assertEqual("deepseek-chat", config["model"])
        self.assertEqual("sk-test123", config["api_key"])

    def test_blank_key_on_save_keeps_existing(self) -> None:
        path = self._config()
        llm_config.save_config(
            path, provider="deepseek", api_key="sk-original", model="m"
        )
        llm_config.save_config(
            path, provider="deepseek", api_key="", model="deepseek-chat"
        )
        config = llm_config.load_config(path)
        self.assertEqual("sk-original", config["api_key"])
        self.assertEqual("deepseek-chat", config["model"])

    def test_blank_key_with_no_existing_key_raises(self) -> None:
        path = self._config()
        with self.assertRaises(ValueError):
            llm_config.save_config(path, provider="deepseek", api_key="", model="m")

    def test_public_config_never_contains_api_key(self) -> None:
        path = self._config()
        llm_config.save_config(
            path, provider="deepseek", api_key="sk-super-secret", model="m"
        )
        public = llm_config.public_config(llm_config.load_config(path))
        self.assertNotIn("sk-super-secret", json.dumps(public))
        self.assertTrue(public["has_api_key"])
        self.assertIn("sk-super-secret"[-4:], public["key_masked"])

    def test_mask_format(self) -> None:
        self.assertTrue(llm_config.mask_key("sk-abc12345").startswith("sk-"))
        self.assertEqual("***", llm_config.mask_key(""))

    def test_get_api_key_store_before_env(self) -> None:
        path = self._config()
        llm_config.save_config(path, provider="deepseek", api_key="sk-store", model="m")
        with mock.patch.dict("os.environ", {"DEEPSEEK_API_KEY": "sk-env"}):
            self.assertEqual("sk-store", llm_config.get_api_key(path, "deepseek"))


class LlmAdapterTests(unittest.TestCase):
    def test_chat_request_shape(self) -> None:
        request = llm_adapter.build_chat_request(
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
            prompt="hello",
            params={"max_tokens": 4096},
            key="sk-key",
        )
        self.assertEqual(
            "https://api.deepseek.com/chat/completions", request["url"]
        )
        self.assertEqual("application/json", request["headers"]["Content-Type"])
        body = json.loads(request["body"])
        self.assertEqual("deepseek-chat", body["model"])
        self.assertEqual("hello", body["messages"][-1]["content"])
        self.assertEqual(4096, body["max_tokens"])
        self.assertEqual("Bearer sk-key", request["headers"]["Authorization"])

    def test_responses_request_shape_is_distinct(self) -> None:
        request = llm_adapter.build_responses_request(
            base_url="https://api.example.com",
            model="some-model",
            prompt="hello",
            params={"max_output_tokens": 2048},
            key="sk-key",
        )
        self.assertEqual("https://api.example.com/responses", request["url"])
        body = json.loads(request["body"])
        self.assertEqual("some-model", body["model"])
        self.assertEqual("hello", body["input"])
        self.assertEqual(2048, body["max_output_tokens"])
        self.assertNotIn("messages", body)

    def test_parse_chat_content_none_with_reasoning_is_valid(self) -> None:
        data = {
            "choices": [
                {
                    "message": {
                        "content": None,
                        "reasoning_content": "thinking trace...",
                    }
                }
            ]
        }
        text, ok = llm_adapter.parse_chat_response(data)
        self.assertTrue(ok)
        self.assertEqual("", text)

    def test_parse_chat_normal_content(self) -> None:
        data = {"choices": [{"message": {"content": "## Facts used\n..."}}]}
        text, ok = llm_adapter.parse_chat_response(data)
        self.assertTrue(ok)
        self.assertIn("Facts used", text)

    def test_parse_chat_missing_choices_raises(self) -> None:
        with self.assertRaises(llm_adapter.LLMError) as ctx:
            llm_adapter.parse_chat_response({})
        self.assertEqual("invalid_response", ctx.exception.error_type)

    def test_parse_responses_uses_output_output_text(self) -> None:
        data = {
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": "body"}],
                }
            ]
        }
        text, ok = llm_adapter.parse_responses_response(data)
        self.assertTrue(ok)
        self.assertEqual("body", text)

    def test_completion_error_mapping(self) -> None:
        cases = {
            401: "auth",
            403: "auth",
            404: "not_found",
            429: "rate_limited",
            500: "server_error",
        }
        for status, error_type in cases.items():
            with mock.patch(
                "research_os.llm._http.http_request",
                _http(status, {"error": "x"}),
            ):
                with self.assertRaises(llm_adapter.LLMError) as ctx:
                    llm_adapter.chat_completion(
                        base_url="https://api.deepseek.com",
                        key="sk-key",
                        model="deepseek-chat",
                        prompt="hi",
                        params={},
                        timeout=30,
                    )
                self.assertEqual(error_type, ctx.exception.error_type, status)

    def test_completion_timeout_maps(self) -> None:
        with mock.patch(
            "research_os.llm._http.http_request",
            mock.Mock(side_effect=TimeoutError("slow")),
        ):
            with self.assertRaises(llm_adapter.LLMError) as ctx:
                llm_adapter.chat_completion(
                    base_url="https://api.deepseek.com",
                    key="sk-key",
                    model="deepseek-chat",
                    prompt="hi",
                    params={},
                    timeout=30,
                )
            self.assertEqual("timeout", ctx.exception.error_type)

    def test_test_connection_ok_with_empty_content(self) -> None:
        # content:null + reasoning_content is a SUCCESS for connectivity
        data = {
            "choices": [
                {"message": {"content": None, "reasoning_content": "trace"}}
            ]
        }
        with mock.patch(
            "research_os.llm._http.http_request", _http(200, data)
        ):
            result = llm_adapter.test_connection(
                base_url="https://api.deepseek.com",
                api_format="openai_chat",
                key="sk-key",
                model="deepseek-chat",
                timeout=30,
            )
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(result["latency_ms"], 0)

    def test_test_connection_auth_failure(self) -> None:
        with mock.patch(
            "research_os.llm._http.http_request",
            _http(401, {"error": {"message": "bad key"}}),
        ):
            result = llm_adapter.test_connection(
                base_url="https://api.deepseek.com",
                api_format="openai_chat",
                key="sk-bad",
                model="deepseek-chat",
                timeout=30,
            )
        self.assertFalse(result["ok"])
        self.assertNotIn("sk-bad", json.dumps(result))


class ModelFetchTests(unittest.TestCase):
    def test_fetch_models_sorted_and_normalized(self) -> None:
        data = {
            "data": [
                {"id": "deepseek-chat", "owned_by": "deepseek"},
                {"id": "deepseek-coder", "owned_by": "deepseek"},
                {"id": "deepseek-reasoner", "owned_by": "deepseek"},
            ]
        }
        with mock.patch("research_os.llm._http.http_request", _http(200, data)):
            models = model_fetch.fetch_models(
                base_url="https://api.deepseek.com", key="sk-key", timeout=30
            )
        self.assertEqual(
            ["deepseek-chat", "deepseek-coder", "deepseek-reasoner"],
            [m["id"] for m in models],
        )
        self.assertTrue(all("ownedBy" in m for m in models))

    def test_fetch_models_error_mapping(self) -> None:
        cases = {
            401: "auth",
            404: "not_found",
            429: "rate_limited",
            500: "server_error",
        }
        for status, error_type in cases.items():
            with mock.patch(
                "research_os.llm._http.http_request",
                _http(status, {"error": "x"}),
            ):
                with self.assertRaises(model_fetch.LLMError) as ctx:
                    model_fetch.fetch_models(
                        base_url="https://api.deepseek.com",
                        key="sk-key",
                        timeout=30,
                    )
                self.assertEqual(error_type, ctx.exception.error_type, status)

    def test_fetch_models_timeout(self) -> None:
        with mock.patch(
            "research_os.llm._http.http_request",
            mock.Mock(side_effect=TimeoutError("slow")),
        ):
            with self.assertRaises(model_fetch.LLMError) as ctx:
                model_fetch.fetch_models(
                    base_url="https://api.deepseek.com", key="sk-key", timeout=30
                )
            self.assertEqual("timeout", ctx.exception.error_type)

    def test_fetch_models_invalid_json(self) -> None:
        with mock.patch(
            "research_os.llm._http.http_request", _http(200, {}, raw="not-json{")
        ):
            with self.assertRaises(model_fetch.LLMError) as ctx:
                model_fetch.fetch_models(
                    base_url="https://api.deepseek.com", key="sk-key", timeout=30
                )
            self.assertEqual("invalid_response", ctx.exception.error_type)

    def test_key_never_leaks_in_output_or_error(self) -> None:
        with mock.patch(
            "research_os.llm._http.http_request", _http(401, {"error": "x"})
        ), self.assertRaises(model_fetch.LLMError) as ctx:
            model_fetch.fetch_models(
                base_url="https://api.deepseek.com", key="sk-topsecret", timeout=30
            )
        self.assertNotIn("sk-topsecret", str(ctx.exception))


class ModelAdapterProtocolTests(unittest.TestCase):
    def _adapter(self):
        try:
            from research_os.adapters.model import DeepSeekAdapter, build_adapter
        except ModuleNotFoundError as exc:
            raise unittest.SkipTest("deepseek adapter not yet wired") from exc
        return build_adapter, DeepSeekAdapter

    def test_build_adapter_deepseek(self) -> None:
        build_adapter, DeepSeekAdapter = self._adapter()
        self.assertIsInstance(build_adapter("deepseek"), DeepSeekAdapter)

    def test_echo_adapter_ignores_model_args(self) -> None:
        from research_os.adapters.model import EchoAdapter

        adapter = EchoAdapter()
        self.assertEqual(
            "hi",
            adapter.generate(
                "hi", model_id="deepseek-chat", model_parameters={"temperature": "0.2"}
            ),
        )

    def test_deepseek_generate_resolves_key_from_config(self) -> None:
        build_adapter, _ = self._adapter()
        with tempfile.TemporaryDirectory() as temp:
            config_path = Path(temp) / "llm.local.json"
            llm_config.save_config(
                config_path,
                provider="deepseek",
                api_key="sk-store",
                model="deepseek-chat",
            )
            data = {"choices": [{"message": {"content": "## Facts used\nok"}}]}
            with mock.patch(
                "research_os.llm._http.http_request", _http(200, data)
            ), mock.patch(
                "research_os.llm.provider_catalog.get_preset"
            ), mock.patch.object(
                llm_config, "CONFIG_PATH", config_path
            ):
                from research_os.adapters.model import DeepSeekAdapter

                adapter = DeepSeekAdapter()
                text = adapter.generate("prompt", model_id="deepseek-chat")
            self.assertIn("Facts used", text)

    def test_deepseek_generate_without_key_raises_guidance(self) -> None:
        from research_os.adapters.model import DeepSeekAdapter

        with mock.patch.object(
            llm_config, "get_api_key", return_value=""
        ), mock.patch.object(
            llm_config, "CONFIG_PATH", Path("/nonexistent/llm.local.json")
        ):
            adapter = DeepSeekAdapter()
            with self.assertRaises(ValueError) as ctx:
                adapter.generate("prompt", model_id="deepseek-chat")
        self.assertIn("API key", str(ctx.exception))


class LlmDashboardTests(unittest.TestCase):
    def test_llm_page_renders(self) -> None:
        from fastapi.testclient import TestClient

        from research_os.ui.app import create_app

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.object(llm_config, "CONFIG_PATH", root / "llm.local.json"):
                client = TestClient(create_app(root))
                page = client.get("/llm")
                self.assertEqual(200, page.status_code)
                self.assertIn("模型供应商", page.text)
                self.assertIn("deepseek", page.text)

    def test_models_endpoint_returns_sorted_no_key(self) -> None:
        from fastapi.testclient import TestClient

        from research_os.ui.app import create_app

        data = {
            "data": [
                {"id": "deepseek-reasoner", "owned_by": "deepseek"},
                {"id": "deepseek-chat", "owned_by": "deepseek"},
            ]
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch(
                "research_os.llm._http.http_request", _http(200, data)
            ), mock.patch.object(llm_config, "CONFIG_PATH", root / "llm.local.json"):
                client = TestClient(create_app(root))
                response = client.post(
                    "/llm/models",
                    json={"provider": "deepseek", "api_key": "sk-tmp"},
                )
                self.assertEqual(200, response.status_code)
                body = response.json()
                ids = [m["id"] for m in body["models"]]
                self.assertEqual(["deepseek-chat", "deepseek-reasoner"], ids)
                self.assertNotIn("sk-tmp", response.text)

    def test_config_save_blank_key_keeps_existing(self) -> None:
        from fastapi.testclient import TestClient

        from research_os.ui.app import create_app

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = root / "llm.local.json"
            with mock.patch.object(llm_config, "CONFIG_PATH", config_path):
                client = TestClient(create_app(root))
                client.post(
                    "/llm/config",
                    json={"provider": "deepseek", "api_key": "sk-keep", "model": "m1"},
                )
                client.post(
                    "/llm/config",
                    json={"provider": "deepseek", "api_key": "", "model": "m2"},
                )
                saved = llm_config.load_config(config_path)
                self.assertEqual("sk-keep", saved["api_key"])
                self.assertEqual("m2", saved["model"])
                public = client.get("/llm/config").json()
                self.assertNotIn("sk-keep", response_text(public))


def response_text(public: dict) -> str:
    return json.dumps(public)


class LlmE2ETests(unittest.TestCase):
    """Real DeepSeek connectivity — runs only when DEEPSEEK_API_KEY is set."""

    @unittest.skipUnless(
        __import__("os").environ.get("DEEPSEEK_API_KEY"), "DEEPSEEK_API_KEY not set"
    )
    def test_deepseek_connectivity(self) -> None:
        import os

        key = os.environ["DEEPSEEK_API_KEY"]
        result = llm_adapter.test_connection(
            base_url=provider_catalog.get_preset("deepseek").base_url,
            api_format="openai_chat",
            key=key,
            model="deepseek-chat",
            timeout=60,
        )
        self.assertTrue(result["ok"], result)
        models = model_fetch.fetch_models(
            base_url=provider_catalog.get_preset("deepseek").base_url,
            key=key,
            timeout=60,
        )
        self.assertGreater(len(models), 0)


if __name__ == "__main__":
    unittest.main()
