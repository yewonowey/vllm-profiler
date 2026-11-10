#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail
repo=$(realpath "$(dirname -- "${BASH_SOURCE[0]}")/../../..")
python3 - "$repo" "$@" <<'PY'
import argparse
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

REPO = Path(sys.argv.pop(1))
MAX_BYTES = 100 * 1024 * 1024


def git(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def main():
    parser = argparse.ArgumentParser(description="Package an existing clean release tag.")
    for name in ("out", "offline-bundle", "sweep-dir", "opprofile-dir"):
        parser.add_argument("--" + name, type=lambda p: Path(p).expanduser().resolve(), required=True)
    parser.add_argument("--tag", required=True)
    args = parser.parse_args()
    if args.out.is_relative_to(REPO):
        raise ValueError("--out must be outside repository")
    ref = "refs/tags/" + args.tag
    commit = git("rev-parse", "--verify", ref + "^{commit}").decode().strip()
    if git("status", "--porcelain", "--untracked-files=all").strip():
        raise ValueError("working tree is dirty")
    git("rev-parse", "--verify", "refs/heads/main")
    subprocess.run(["sha256sum", "--check", "--quiet", "SHA256SUMS"],
                   cwd=args.offline_bundle, check=True)
    if not (args.sweep_dir / "dataset").is_dir() or not args.opprofile_dir.is_dir():
        raise ValueError("sweep dataset or operator directory is missing")
    summaries = sorted(args.sweep_dir.glob("runs/*/*/profile/summary.json"))
    if not summaries:
        raise ValueError("no representative profile/summary.json in sweep")
    root = args.out / ("etri-pdd-perf-" + quote(args.tag, safe=""))
    root.mkdir(parents=True, exist_ok=False)
    for name in ("docs", "dataset", "samples", "LICENSES"):
        (root / name).mkdir()
    git("bundle", "create", str(root / "repo.bundle"), "refs/heads/main", ref)
    archive = git("archive", "--format=tar", commit + ":docs/hetero")
    subprocess.run(["tar", "-x", "-C", str(root / "docs")], input=archive, check=True)
    shutil.copytree(args.offline_bundle, root / "offline_bundle")
    for name in ("LICENSE", "NOTICE"):
        shutil.copy2(args.offline_bundle / name, root / "LICENSES" / ("offline_" + name))
    shutil.copytree(args.offline_bundle / "licenses", root / "LICENSES" / "wheel_notices")
    (root / "LICENSES" / "repository_LICENSE").write_bytes(git("show", commit + ":LICENSE"))
    (root / "LICENSES" / "LGPL_MPL_NOTICE.md").write_text(
        "# 포함 구성물 고지\n\n"
        "setuptools의 autocommand는 LGPL-3.0, pip의 certifi 및 일부 포함 코드는 MPL 고지를 가진다.\n"
        "wheel_notices/의 원문과 docs/third_party_licenses.md를 함께 제공한다.\n"
        "최상위 MIT 표기로 포함물 조건을 대체하지 않는다. 수정·재배포 시 해당 소스 제공 및 고지 요건을 확인한다.\n"
        "이 패키지 생성은 그 요건의 최종 이행 판정이 아니다.\n"
    )
    omitted = []

    def copy_small(source, target):
        if source.is_symlink() or source.stat().st_size > MAX_BYTES:
            omitted.append(str(target.relative_to(root)) + " (symlink or >100 MiB)")
            return
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True

    dataset = args.sweep_dir / "dataset"
    for path in sorted(dataset.rglob("*")):
        if path.is_file() and (path.suffix == ".csv" or path.name == "DATA_DICTIONARY.md"):
            copy_small(path, root / "dataset" / path.relative_to(dataset))
    for path in sorted(args.opprofile_dir.rglob("*.csv")):
        if path.name in ("operators.csv", "operators_by_type.csv", "kernel_steps.csv"):
            copy_small(path, root / "dataset" / "opprofile" / path.relative_to(args.opprofile_dir))
    chosen = set()
    for path in summaries:
        run = path.parents[2].name
        if run not in chosen and len(chosen) < 2:
            if copy_small(path, root / "samples" / run / path.parents[1].name / "summary.json"):
                chosen.add(run)
    if not chosen:
        raise ValueError("no representative summary within the 100 MiB limit")
    for path in sorted((args.sweep_dir / "figures").glob("*.png")):
        copy_small(path, root / "samples" / "figures" / path.name)

    def section(file, heading):
        text = (root / "docs" / file).read_text()
        return heading + text.split(heading, 1)[1].split("\n## ", 1)[0]

    notes = (
        f"# etri-pdd-perf-{args.tag}\n\n태그: {args.tag}\n커밋: {commit}\n\n"
        "repo.bundle: main과 지정 태그의 이력. docs와 저장소 LICENSE는 태그 커밋에서 추출.\n"
        "offline_bundle: 지정 오프라인 번들과 SHA256SUMS. dataset: sweep CSV·사전 및 연산자 CSV.\n"
        "samples: 이름순 서로 다른 실행 최대 2건의 첫 workload summary와 sweep 그림.\n"
        "LICENSES: 저장소·번들·포함 wheel 고지. 원본 trace, 모델, SDK, CUDA/RBLN venv는 제외.\n"
        "자료 선별은 CSV·사전·대표 summary·PNG 허용 목록과 파일당 100 MiB 제한을 적용한다.\n"
        "제한은 repo.bundle·offline_bundle·태그 문서에는 적용하지 않는다.\n"
        "패키지 생성 성공은 IT-03 또는 최종 납품 합격이 아니다.\n\n"
        "# 알려진 한계 (태그 문서에서 발췌)\n\n"
        + section("security_check.md", "## 1. 범위와 결론") + "\n"
        + section("final_report_analysis.md", "## 10. 한계와 미확인 사항")
        + "\n## 추가 제외 파일\n\n" + ("\n".join(omitted) or "없음") + "\n"
    )
    (root / "RELEASE_NOTES.md").write_text(notes)
    with (root / "MANIFEST.sha256").open("w") as manifest:
        for path in sorted(root.rglob("*")):
            if path.is_file() and path != root / "MANIFEST.sha256":
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                manifest.write(f"{digest.hexdigest()}  {path.relative_to(root)}\n")
    print(f"make_release: {root.name}: {commit}")


try:
    main()
except Exception as exc:
    print(f"make_release: {type(exc).__name__}: {exc}", file=sys.stderr)
    sys.exit(1)
PY
