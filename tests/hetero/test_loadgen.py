# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlsplit

from tests.hetero.mock_proxy import MockProxy
from tests.hetero.mock_server import MockServer
from tools.hetero import loadgen

CALCULATED = set(
    [
        "ttft_seconds",
        "tp_ot_seconds",
        "e2e_seconds",
        "service_seconds",
        "queue_wait_seconds",
        "second_token_delay_seconds",
        "token_itl_seconds",
        "chunk_itl_seconds",
        "token_itl_available",
        "client_send_delay_seconds",
        "success",
    ]
)


class FakeTokenizer:
    def encode(self, text, **_kwargs):
        return [ord(char) for char in text]


class LoadgenTests(unittest.TestCase):
    def test_raw_records_routes_and_anchors(self):
        real = next(
            (Path(__file__).parent / "fixtures" / "real").glob("*/*/requests.jsonl")
        )
        raw_keys = json.loads(real.read_text().splitlines()[0]).keys() - CALCULATED
        for mode in ("gpu", "baseline", "pdd"):
            with (
                self.subTest(mode=mode),
                tempfile.TemporaryDirectory() as temp,
                ExitStack() as stack,
            ):
                servers = [stack.enter_context(MockServer()) for _ in range(3)]
                if mode == "baseline":
                    routing = [
                        arg
                        for role, server in zip(("gpu", "npu0", "npu1"), servers)
                        for arg in ("--worker", f"{role}={server.url}=1")
                    ]
                else:
                    url = servers[0].url
                    if mode == "pdd":
                        servers[0].role = "prefill"
                        url = stack.enter_context(
                            MockProxy(
                                url, [s.url for s in servers[1:]], pattern=[1, 0, 1]
                            )
                        ).url
                    routing = ["--endpoint", url, "--target", mode]
                argv = [
                    *routing,
                    "--model",
                    "mock",
                    "--tokenizer",
                    "unused",
                    "--input-tokens",
                    "8",
                    "--output-tokens",
                    "3",
                    "--requests",
                    "3",
                    "--workload",
                    "smoke",
                    "--seed",
                    "7",
                    "--warmup-per-endpoint",
                    "0",
                    "--run-dir",
                    temp,
                ]
                loadgen.main(argv, tokenizer=FakeTokenizer())
                directory = Path(temp)
                rows = [
                    json.loads(s)
                    for s in (directory / "requests.jsonl").read_text().splitlines()
                ]
                self.assertEqual(len(rows), 3)
                for row in rows:
                    self.assertEqual(set(row), raw_keys)
                    self.assertEqual(
                        (row["actual_input_tokens"], row["actual_output_tokens"]),
                        (8, 3),
                    )
                    self.assertTrue(row["chunk_timestamps"])
                expected = {"gpu", "npu0", "npu1"} if mode == "baseline" else {mode}
                self.assertEqual({r["assigned_target"] for r in rows}, expected)
                if mode == "pdd":
                    self.assertEqual(
                        [r["response_headers"]["x-decode-target"] for r in rows],
                        [urlsplit(servers[i].url).netloc for i in (2, 1, 2)],
                    )
                run = json.loads((directory / "loadgen_run.json").read_text())
                self.assertEqual(run["argv"], argv)
                self.assertTrue(run["slots"])
                for key in ("clock_anchor_start", "clock_anchor_end"):
                    self.assertEqual(set(run[key]), {"time_ns", "monotonic_ns"})
                    self.assertTrue(
                        all(type(value) is int for value in run[key].values())
                    )
                self.assertLess(
                    run["clock_anchor_start"]["monotonic_ns"],
                    run["clock_anchor_end"]["monotonic_ns"],
                )
                self.assertEqual(run["arrival"], rows[0]["scheduled_arrival_monotonic"])
                self.assertFalse((directory / "summary.json").exists())

    def test_warmup_only_success_and_failure(self):
        for failed in (False, True):
            with (
                self.subTest(failed=failed),
                tempfile.TemporaryDirectory() as temp,
                MockServer(
                    fail_ids=("smoke-warmup-seed7-req-001",) if failed else ()
                ) as server,
            ):
                argv = [
                    "--endpoint",
                    server.url,
                    "--model",
                    "mock",
                    "--tokenizer",
                    "unused",
                    "--input-tokens",
                    "8",
                    "--output-tokens",
                    "3",
                    "--requests",
                    "1",
                    "--workload",
                    "smoke",
                    "--seed",
                    "7",
                    "--warmup-only",
                    "--out-dir",
                    temp,
                ]
                if failed:
                    with self.assertRaisesRegex(RuntimeError, "warmup failed"):
                        loadgen.main(argv, tokenizer=FakeTokenizer())
                else:
                    loadgen.main(argv, tokenizer=FakeTokenizer())
                self.assertEqual(
                    {p.name for p in Path(temp).iterdir()}, {"warmup_requests.jsonl"}
                )
                row = json.loads((Path(temp) / "warmup_requests.jsonl").read_text())
                self.assertFalse(CALCULATED & row.keys())
                self.assertEqual(row["http_status"], 500 if failed else 200)
