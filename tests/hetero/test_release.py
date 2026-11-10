# SPDX-License-Identifier: Apache-2.0
import shutil
import subprocess
import tempfile
import unittest
from functools import partial
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = Path("tools/hetero/third_party/make_release.sh")

call = partial(subprocess.run, capture_output=True, text=True, check=True)


class ReleaseTests(unittest.TestCase):
    def test_release(self):
        with tempfile.TemporaryDirectory() as temp:
            root, repo = Path(temp), Path(temp) / "repo"
            for name in ("tools/hetero/third_party", "docs/hetero"):
                shutil.copytree(REPO / name, repo / name)
            (repo / "LICENSE").write_text("license")
            git = lambda *args: call(["git", "-C", str(repo), *args])
            git("init", "-b", "main")
            git("add", ".")
            git("-c", "user.name=T", "-c", "user.email=t@x", "commit", "-qm", "fixture")
            git("tag", "vtest")
            names = (
                "offline-bundle/LICENSE offline-bundle/NOTICE "
                "offline-bundle/licenses/MIT sweep-dir/dataset/runs.csv "
                "sweep-dir/dataset/trace.json.gz opprofile-dir/npu/operators.csv "
                "opprofile-dir/npu/raw.pb sweep-dir/figures/test.png "
                "sweep-dir/runs/s1_b0/s1/profile/summary.json"
            )
            for name in names.split():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture\n")
            bundle = root / "offline-bundle"
            (bundle / "SHA256SUMS").write_text(
                call(["sha256sum", "LICENSE"], cwd=bundle).stdout
            )
            with (root / "sweep-dir/dataset/large.csv").open("wb") as stream:
                stream.truncate(100 * 1024 * 1024 + 1)
            command = ["bash", str(repo / SCRIPT)]
            for key in ("offline-bundle", "sweep-dir", "opprofile-dir"):
                command += ["--" + key, str(root / key)]
            release = root / "etri-pdd-perf-vtest"
            for case in ("inside", "missing", "dirty", "valid"):
                out = repo if case == "inside" else root
                tag = "absent" if case == "missing" else "vtest"
                (repo / "LICENSE").write_text("dirty" if case == "dirty" else "license")
                result = call([*command, "--out", str(out), "--tag", tag], check=False)
                failed = case != "valid"
                self.assertEqual(result.returncode != 0, failed, result.stderr)
                self.assertEqual(release.exists(), not failed)
            expected = "repo.bundle offline_bundle docs dataset samples LICENSES "
            expected += "RELEASE_NOTES.md MANIFEST.sha256"
            self.assertEqual(set(expected.split()), {p.name for p in release.iterdir()})
            call(["sha256sum", "-c", "MANIFEST.sha256"], cwd=release)
            files = {p.name for p in release.rglob("*")}
            self.assertTrue({"operators.csv", "summary.json", "test.png"} <= files)
            self.assertFalse({"raw.pb", "trace.json.gz", "large.csv"} & files)

    def test_workflow_yaml(self):
        try:
            import yaml
        except ImportError:
            self.skipTest("PyYAML not installed")
        for name in ("hetero_unit_tests", "hetero_profile"):
            data = yaml.safe_load((REPO / f".github/workflows/{name}.yml").read_text())
            self.assertIn("workflow_dispatch", data["on"])
            self.assertTrue(data["jobs"])
