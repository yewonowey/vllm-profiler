# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from tests.hetero.fakes import FakePopen
from tools.hetero import orchestrate as harness


def start_args(directory, *extra, configuration="pdd"):
    return harness.parse_args(
        [
            "start",
            "--configuration",
            configuration,
            "--run-dir",
            str(directory / "run"),
            "--model-path",
            str(directory),
            "--model-name",
            "mock",
            "--cuda-python",
            sys.executable,
            "--rbln-python",
            sys.executable,
            *extra,
        ]
    )


class OrchestrateTests(unittest.TestCase):
    def test_python_path_precedence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for explicit, variable, expected in (
                (directory / "cli", str(directory / "env"), directory / "cli"),
                (None, str(directory / "env"), directory / "env"),
                (None, "", None),
            ):
                with (
                    self.subTest(explicit=explicit, variable=variable),
                    patch.dict(os.environ, {"CUDA_PY": variable}),
                ):
                    if expected is None:
                        with self.assertRaises(ValueError):
                            harness.python_path(explicit, "CUDA_PY")
                    else:
                        self.assertEqual(
                            harness.python_path(explicit, "CUDA_PY"), expected
                        )

    def test_role_option_rejections(self):
        cases = [
            ("--role-env-json", {"decode0": {"bad-key": "1"}}),
            ("--role-env-json", {"decode0": {"GOOD": "line\nbreak"}}),
            ("--role-env-json", {"decode0": {"GOOD": "nul\0byte"}}),
            ("--role-env-json", {"decode0": {"GOOD": 1}}),
            ("--role-env-json", {"missing": {"GOOD": "1"}}),
            ("--role-env-json", {"gpu": {"GOOD": "1"}}),
            ("--role-args-json", {"decode0": ["--port", "1"]}),
            ("--role-args-json", {"decode0": ["--profiler-config"]}),
            ("--role-args-json", {"decode0": ["--profiler-config", "--port"]}),
            ("--role-args-json", {"missing": []}),
        ]
        with tempfile.TemporaryDirectory() as temp:
            for option, value in cases:
                with (
                    self.subTest(option=option, value=value),
                    self.assertRaises(ValueError),
                ):
                    start_args(Path(temp), option, json.dumps(value))

    def test_clean_repository_and_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)

            def git(*args):
                subprocess.run(
                    ["git", "-C", str(repo), *args], check=True, capture_output=True
                )

            git("init")
            tracked = repo / "tracked"
            tracked.write_text("initial")
            git("add", "tracked")
            git(
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "-m",
                "fixture",
            )
            (repo / ".git" / "info" / "exclude").write_text("local-only\n")
            (repo / "local-only").write_text("ignored")
            original = harness.run_checked

            def checked(argv):
                if argv[0] == "git":
                    return original(argv)
                if "rebel-compiler" in argv[-1]:
                    return "fixture-compiler"
                return "0.22.0" if argv[0] == "cuda" else "0.22.0+cpu"

            with patch.object(harness, "run_checked", side_effect=checked):
                result = harness.verify_environment(repo, Path("cuda"), Path("rbln"))
                self.assertTrue(result["commit"])
                self.assertEqual(result["compiler"], "fixture-compiler")
                with self.assertRaisesRegex(RuntimeError, "compiler mismatch"):
                    harness.verify_environment(
                        repo, Path("cuda"), Path("rbln"), "other"
                    )
                tracked.write_text("modified")
                with self.assertRaisesRegex(RuntimeError, "dirty"):
                    harness.verify_environment(repo, Path("cuda"), Path("rbln"))

    def test_launch_options_and_failure_cleanup(self):
        for failure in (False, True):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temp,
                ExitStack() as stack,
            ):
                directory = Path(temp)
                args = start_args(
                    directory,
                    "--layout-reorder",
                    "1",
                    "--cache-dir",
                    str(directory / "cache"),
                    "--role-env-json",
                    json.dumps({"decode0": {"TEST_TAG": "ok"}}),
                    "--role-args-json",
                    json.dumps({"decode0": ["--profiler-config", "{}"]}),
                )
                popen = FakePopen()
                for name, value in (
                    ("verify_environment", {}),
                    ("verify_idle", {}),
                    ("proc_starttime", 1),
                ):
                    stack.enter_context(patch.object(harness, name, return_value=value))
                stack.enter_context(patch.object(harness.subprocess, "Popen", popen))
                stack.enter_context(
                    patch.object(harness.os, "getpgid", side_effect=lambda pid: pid)
                )
                stack.enter_context(patch.object(harness.time, "sleep"))
                ready = stack.enter_context(patch.object(harness, "wait_http"))
                stop = stack.enter_context(patch.object(harness, "stop_records"))
                stack.enter_context(redirect_stdout(StringIO()))
                if failure:
                    ready.side_effect = [None, RuntimeError("unready")]
                    with self.assertRaisesRegex(RuntimeError, "unready"):
                        harness.start(args)
                    stop.assert_called_once_with(directory / "run")
                    self.assertEqual(len(popen.calls), 2)
                else:
                    harness.start(args)
                    config = json.loads((directory / "run" / "config.json").read_text())
                    self.assertEqual(
                        [r["role"] for r in config["processes"]],
                        ["prefill", "decode0", "decode1", "proxy"],
                    )
                    self.assertEqual(popen.calls[1]["env"]["TEST_TAG"], "ok")
                    self.assertEqual(
                        popen.calls[1]["env"]["VLLM_RBLN_PDD_LAYOUT_REORDER"], "1"
                    )
                    self.assertEqual(
                        popen.calls[1]["argv"][-2:], ["--profiler-config", "{}"]
                    )
                    self.assertEqual(
                        popen.calls[1]["env"]["VLLM_CACHE_ROOT"],
                        str(directory / "cache" / "npu_shared"),
                    )
                    self.assertEqual(
                        set(config["metrics_endpoints"]),
                        {"prefill", "decode0", "decode1"},
                    )
                    self.assertEqual(
                        set(config["decoder_roles"].values()), {"decode0", "decode1"}
                    )
                    self.assertEqual(
                        config["kv_buffer_device"], {"decode0": "cpu", "decode1": "cpu"}
                    )
