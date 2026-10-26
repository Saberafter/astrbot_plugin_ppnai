"""Offline account-query coverage, without AstrBot or NovelAI credentials."""

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import httpx


def load_handlers():
    audit = ModuleType("_ppnai_accounts_test.anlas_audit")
    audit.recent_entries = lambda limit: []
    spec = importlib.util.spec_from_file_location(
        "_ppnai_accounts_test.handlers_admin",
        Path(__file__).resolve().parents[1] / "src" / "handlers_admin.py",
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"_ppnai_accounts_test.anlas_audit": audit}):
        spec.loader.exec_module(module)
    return module


handlers = load_handlers()


class UsageFormattingTests(unittest.TestCase):
    def test_remaining_percentage_and_subscription_states(self):
        cases = [
            ({"percent": 79}, "79%"),
            ({"percent": 41.625}, "41.625%"),
            ({"percent": 196}, "196%"),
            ({"percent": 0}, "0%"),
            ({"percent": -3}, "0%"),
            ({"percent": 79, "isNegative": True}, "0%（额度已透支）"),
            ({"percent": True}, "官方未返回有效额度"),
            ({"percent": "79"}, "官方未返回有效额度"),
            ({"percent": float("nan")}, "官方未返回有效额度"),
            ({"percent": float("inf")}, "官方未返回有效额度"),
            ({}, "官方未返回有效额度"),
            (None, "官方未返回有效额度"),
            ([], "官方未返回有效额度"),
        ]
        for usage, expected in cases:
            with self.subTest(usage=usage):
                result = handlers._format_opus_usage(
                    {"tier": 3, "active": True, "usage": usage}
                )
                self.assertEqual(result, "生图额度剩余：" + expected)
        for active, tier, expected in [
            (False, 3, "不可用（订阅未激活）"),
            (True, 2, "不适用（非 Opus 订阅）"),
            (True, 4, "79%"),
        ]:
            with self.subTest(active=active, tier=tier):
                result = handlers._format_opus_usage(
                    {"tier": tier, "active": active, "usage": {"percent": 79}}
                )
                self.assertEqual(result, "生图额度剩余：" + expected)


class AccountQueryTests(unittest.IsolatedAsyncioTestCase):
    def plugin(self, *, allowed=True, tokens=None, proxy=""):
        return SimpleNamespace(
            _check_permission=lambda event: allowed,
            config=SimpleNamespace(
                request=SimpleNamespace(
                    tokens=["synthetic-good", "synthetic-failed"] if tokens is None else tokens,
                    proxy_url=proxy,
                )
            ),
        )

    async def collect(self, plugin):
        event = SimpleNamespace(plain_result=lambda text: text)
        return [result async for result in handlers.handle_nai_accounts(plugin, event)]

    async def test_permission_and_empty_tokens_do_not_request(self):
        with patch.object(handlers.httpx, "AsyncClient") as client:
            denied = await self.collect(self.plugin(allowed=False))
            empty = await self.collect(self.plugin(tokens=["", " "]))
        client.assert_not_called()
        self.assertIn("权限不足", denied[0])
        self.assertIn("未配置", empty[0])

    async def test_multi_account_failure_proxy_and_secret_redaction(self):
        requests = []
        options = []
        real_client = httpx.AsyncClient

        def respond(request):
            requests.append(request)
            if request.headers["Authorization"] == "Bearer synthetic-failed":
                return httpx.Response(401, text="secret upstream failure")
            return httpx.Response(
                200,
                json={
                    "active": True,
                    "tier": 3,
                    "usage": {"percent": 79},
                    "trainingStepsLeft": {
                        "fixedTrainingStepsLeft": 10000,
                        "purchasedTrainingSteps": 0,
                    },
                },
            )

        def client_factory(**kwargs):
            options.append(dict(kwargs))
            kwargs.pop("proxy")
            return real_client(transport=httpx.MockTransport(respond), **kwargs)

        with patch.object(handlers.httpx, "AsyncClient", side_effect=client_factory):
            result = (await self.collect(self.plugin(proxy="http://127.0.0.1:7897")))[0]
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(r.method == "GET" for r in requests))
        self.assertTrue(all(str(r.url) == "https://image.novelai.net/user/subscription" for r in requests))
        self.assertTrue(all(o["proxy"] == "http://127.0.0.1:7897" for o in options))
        self.assertTrue(all(o["trust_env"] is False for o in options))
        self.assertIn("账号 1：Opus，订阅有效", result)
        self.assertIn("生图额度剩余：79%", result)
        self.assertIn("Anlas：订阅 10000，购买 0", result)
        self.assertIn("账号 2：查询失败（HTTPStatusError）", result)
        self.assertIn("北京时间", result)
        self.assertNotIn("synthetic-", result)
        self.assertNotIn("secret upstream", result)


if __name__ == "__main__":
    unittest.main()
