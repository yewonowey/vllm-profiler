# CI·납품 패키지 시험 절차

기준일: 2026-11-10. 로컬 합성 시험과 실제 Actions/HW 설치 시험을 구분한다.
이 문서 작성과 패키징 스크립트 시험만으로 IT-02·IT-03을 합격 처리하지 않는다.
관련 문서: [시험 목록](unit_test_plan.md), [프로파일러 실행](profiler.md),
[보안 점검](security_check.md), [라이선스](third_party_licenses.md).

## IT-02 CI 실행 확인

### 저장소·러너 준비

1. 두 hetero 워크플로를 기본 브랜치에 반영한다. 저장소 Settings → Actions → General에서
   Actions와 사용한 checkout/setup-python/upload-artifact 액션을 허용한다.
   워크플로의 GITHUB_TOKEN 권한은 contents: read다.
2. 실험용 저장소의 Actions 화면에서 이번 시험에 불필요한 기존 워크플로를 각각
   **Disable workflow**로 끈다. 실행 중 작업도 확인한다. 원본 YAML은 수정하지 않는다.
   공유 팀 저장소에서는 담당자와 비활성화 범위를 확인하고, 시험 후 원래 설정으로 복구한다.
3. Settings → Actions → Runners → New self-hosted runner에서 Linux x64 설치·등록 명령을 따른다.
   전용 실행 계정으로 등록하고 기본 self-hosted 라벨에 `hetero-pdd`를 추가한다.
   등록 토큰은 해당 화면에서 받아 사용하며 저장소·문서·로그에 복사하지 않는다.
   `.github/actionlint.yaml`의 같은 라벨은 정적 검사 설정이며 실제 러너 등록을 대신하지 않는다.
4. 러너가 Idle/Online인지, 드라이버·CUDA/RBLN venv·모델·고정 도구가 준비됐는지 확인한다.
   서비스 포트와 장치가 다른 실험에 사용 중이지 않아야 한다.
   워크플로 concurrency는 이 hetero 워크플로끼리만 직렬화하므로 다른 실험까지 막지는 않는다.
5. 저장소 Settings → Secrets and variables → Actions → Variables에 아래 값을 등록한다.
   실제 경로는 저장소 변수나 러너의 비공개 환경 파일에만 둔다.

| 변수 | 위치·형식 |
|---|---|
| `HETERO_ENV_FILE` | 필수 저장소 변수. 저장소 밖에 두고 러너 계정이 읽을 수 있는 셸 환경 파일 경로 |
| `HETERO_RESULTS_ROOT` | 저장소 변수 또는 source되는 환경 파일. 저장소 밖 결과 루트 |
| `HETERO_MODELS_JSON` | 저장소 변수 또는 환경 파일. 모델 키 → 로컬 경로 JSON 객체 |
| `CUDA_PY`, `RBLN_PY` | 환경 파일. 기존 엔진 venv Python 실행 파일 |
| `PDD_TOOLS_PY`, `ALLSMI_BIN`, `OTELCOL_BIN`, `PERFETTO_TP_BIN` | 환경 파일. 설치한 도구 실행 파일 |
| `HETERO_CACHE_ROOT` | 선택, 환경 파일. 공유 캐시 루트. 미설정이면 실행별 캐시 |
| `HETERO_PER001_SCENARIO` | 선택, 환경 파일. PER-001에 재사용할 PDD 단일 workload 시나리오, 기본 `s2_pdd` |

모델 매핑의 형식은 다음과 같다. 실제 값은 아래 자리표시자를 교체해 환경 파일에 설정한다.
환경 파일·러너 환경에 정의한 값이 같은 이름의 저장소 변수보다 우선한다. 환경 파일은 신뢰하는 운영자만 수정한다.

```bash
export HETERO_MODELS_JSON='{"qwen3-0.6b":"<모델 위치 1>","qwen3-4b":"<모델 위치 2>","qwen25-3b":"<모델 위치 3>"}'
export HETERO_RESULTS_ROOT='<저장소 밖 결과 루트>'
```

### 실행·합격 기준

| 단계 | 실행 | 합격 기준 |
|---|---|---|
| IT-02-UT | Actions → Hetero unit tests → Run workflow 또는 tools/hetero·tests/hetero 변경 push | ubuntu-22.04/Python 3.10에서 unittest와 변경 파일 pre-commit 성공 |
| 변경 범위 | push는 before→HEAD, 수동 실행·새 브랜치는 직전 커밋→HEAD, 최초 커밋은 빈 트리→HEAD | 추가·수정·이름 변경 파일 검사, 삭제 파일 제외. 아무 변경 파일도 없으면 훅 실행 없음 |
| 조건부 skip | GPU/RBLN·도구 venv 미설정 상태 | 기존 조건부 시험만 skip, 분석·입력 검증은 실행. SDK를 CI에 설치하지 않음 |
| IT-02-HW | Actions → Hetero profile → Run workflow | 시나리오 JSON·결과 폴더 이름·PER-001 여부 입력, 전용 러너에서 실행 |
| 실행 순서 | sweep.py → finalize_results.py → 선택한 PER-001 | 각 종료 코드 0, 필수 시나리오 run_status·analysis_status PASS |
| 요약 | Actions의 Summary 확인 | results.csv의 상태·처리량·makespan, comparison.csv의 개선율·감소율 표시 |
| artifact | 실행 페이지에서 hetero-results 다운로드 | 결과·dataset CSV·workload summary 존재, 원본 trace·모델·캐시·서비스 로그 없음 |
| 실패 확인 | 의도적으로 잘못된 모델 경로를 지정한 별도 실행 | job 실패 유지, 생성된 CSV·summary는 보존. 실패 실행을 PASS로 덮지 않음 |
| PER-001 | 체크한 경우 PDD workload·서비스 인자를 재사용, mode는 none | overhead.json 판정 PASS, 각 실행 유효성 통과; raw·md 함께 보존 |

수동 워크플로만 추가해도 등록·권한 설정이 완료되는 것은 아니다.
프로파일 워크플로는 pull_request에서 실행되지 않으며, 검토한 브랜치·태그만 수동 실행한다.
전체 스윕 전에 작은 S1 전용 시나리오 파일로 연결·정리·artifact를 먼저 확인한다.
본 측정은 새 결과 폴더 이름을 사용한다. 스윕 자체는 재개 가능하지만 PER-001은 비어 있는 별도 실행 경로가 필요하다.
요약·artifact에는 내부 모델 경로 등이 포함될 수 있으므로 저장소 열람 권한과 보존 정책을 확인한다.
2026-11-10 수동 Actions 42817562993에서 단위시험·pre-commit/actionlint 성공을 확인했다.
최초 SC1090 실패는 source 지시문 주석으로 해결했다. self-hosted는 러너 미등록으로 미실행이며,
합의대로 절차 문서화·actionlint로 갈음한다. HW 실패 시 정리·artifact 실증까지 확인한 것은 아니다.

공식 절차: [수동 실행](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow),
[워크플로 비활성화](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/disable-and-enable-workflows),
[self-hosted 러너 추가](https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners),
[artifact](https://docs.github.com/en/actions/tutorials/store-and-share-data).

## 패키지 생성

태그는 사람이 검토·생성한다. 스크립트는 새 태그를 만들지 않고, tracked 변경과 untracked 파일이
있는 작업 트리를 거부한다. 로컬 전용 무시 파일은 dirty 검사에 포함하지 않는다.
태그와 main 브랜치가 모두 있어야 하며, 기존 출력 패키지를 덮어쓰지 않는다.

```bash
bash tools/hetero/third_party/make_release.sh \
  --out "$RELEASE_OUT" --tag "$RELEASE_TAG" \
  --offline-bundle "$OFFLINE_BUNDLE" \
  --sweep-dir "$SWEEP_DIR" --opprofile-dir "$OPPROFILE_DIR"
```

결과는 `<RELEASE_OUT>/etri-pdd-perf-<tag>/`다. 태그에 파일명 예약 문자가 있으면 URL 인코딩한다.
docs와 저장소 LICENSE는 작업 트리가 아닌 태그 커밋에서 추출한다.
번들은 main·지정 태그의 이력을 담으며, 태그가 현재 HEAD나 main의 끝과 같을 필요는 없다.
오프라인 번들의 기존 SHA256SUMS를 먼저 검사한다. 태그의 versions.env와 호환되는 v2 번들을 지정한다.
그 일치는 설치 단계의 install_offline.sh가 다시 검사한다.

| 포함 위치 | 선택 규칙 |
|---|---|
| `dataset/` | sweep dataset의 CSV·DATA_DICTIONARY.md |
| `dataset/opprofile/` | 원래 상대 폴더를 보존한 operators.csv·operators_by_type.csv·kernel_steps.csv |
| `samples/` | 이름순 서로 다른 실행 최대 2건, 각각 첫 workload의 summary.json |
| `samples/figures/` | sweep figures의 PNG |
| `docs/` | 태그의 docs/hetero 전체, 보고서 그림 포함 |
| `LICENSES/` | 저장소·번들 LICENSE/NOTICE, wheel 고지, LGPL·MPL 안내 |

데이터셋·대표 자료는 파일당 100 MiB를 넘거나 파일 자체가 symlink이면 제외하고 릴리스 노트에 남긴다.
PB·gzip·원본 trace·로그는 허용 목록에 없으므로 복사하지 않는다.
repo.bundle·offline_bundle·태그 문서는 크기 제한의 대상이 아니다.
RELEASE_NOTES에는 태그 보안 점검표의 범위·결론 및 분석 보고서의 한계 절을 발췌한다.
MANIFEST.sha256은 자기 자신을 제외한 모든 파일을 포함한다.

## IT-03 납품 패키지 설치 시험

### 전제

독립된 설치 대상에서 실시한다. 드라이버·SDK, 호환 CUDA/RBLN venv, 로컬 모델은 별도 준비한다.
오프라인 번들의 대상 Python 버전과 설치에 사용하는 python3 버전이 같아야 한다.
`PACKAGE`, `CLONE_DIR`, `TOOLS_VENV`, `TOOLS_DIR`, `S1_RESULTS`, `S1_JSON`은 운영자가 지정한다.
clone을 제외한 설치·결과·임시 시나리오 위치는 clone 저장소 밖이다.
S1_JSON에는 initial.json의 S1 B0·PDD 두 항목만 넣고 쌍 조건·측정 요청 수를 유지한다.

1. **MANIFEST 검증**: 패키지 루트에서 실행해 모든 파일이 OK인지 기록한다.

   ```bash
   (cd "$PACKAGE" && sha256sum --check MANIFEST.sha256)
   ```

2. **bundle clone 및 태그 checkout**: 아직 존재하지 않는 clone 위치를 사용한다.

   ```bash
   git clone --branch main "$PACKAGE/repo.bundle" "$CLONE_DIR"
   git -C "$CLONE_DIR" checkout --detach "$RELEASE_TAG"
   ```

3. **HEAD와 태그 일치**: 출력 두 해시가 같고 릴리스 노트 커밋과도 같아야 한다.

   ```bash
   git -C "$CLONE_DIR" rev-parse HEAD
   git -C "$CLONE_DIR" rev-parse "refs/tags/$RELEASE_TAG^{commit}"
   ```

4. **오프라인 설치**: 저장소 밖 새 venv·바이너리 위치를 사용한다.

   ```bash
   bash "$CLONE_DIR/tools/hetero/third_party/install_offline.sh" \
     --bundle "$PACKAGE/offline_bundle" --venv "$TOOLS_VENV" --tools-dir "$TOOLS_DIR"
   ```

   설치가 출력한 PDD_TOOLS_PY·ALLSMI_BIN·OTELCOL_BIN·PERFETTO_TP_BIN을 운영 환경에 적용한다.
   설치 과정은 no-index이며, CUDA/RBLN venv는 변경하지 않는다.

5. **clean 검사**: 아래 출력이 비어 있어야 한다.

   ```bash
   git -C "$CLONE_DIR" status --porcelain
   ```

6. **단위시험**: clone 루트에서 실행한다. 시스템 python3에는 분석 시험용 prometheus_client가 필요하다.
   완전 오프라인 환경은 이 시험 의존성을 사전 준비하거나 해당 의존성이 있는 CUDA Python을 사용하고 기록한다.

   ```bash
   cd "$CLONE_DIR"
   python3 -m unittest discover -s tests/hetero
   python3 -m unittest discover -s tests/pdd
   ```

   예상된 조건부 skip은 환경과 함께 기록한다. 예기치 않은 실패를 skip으로 바꾸지 않는다.

7. **S1 실행**: 환경 파일을 읽고 두 모델 경로 대신 S1의 모델 하나만 넘긴다.

   ```bash
   source "$HETERO_ENV_FILE"
   "$CUDA_PY" -m tools.hetero.profiler.sweep \
     --scenarios "$S1_JSON" --sweep-dir "$S1_RESULTS" \
     --model "qwen3-0.6b=$QWEN06_PATH"
   ```

   S1 B0·PDD의 run_status·analysis_status PASS, 결과표·비교표 생성, 서비스 종료를 확인한다.
   rc1 IT-03에서 S1 B0·PDD의 단계 전부 성공 및 두 상태 PASS를 확인했다.
   sweep2 대비 처리량·makespan·평균 TTFT/TPOT/E2E는 모두 ±10% 이내였다.
   수치·직접 확인 범위는 [시험 보고서](test_report.md)에 기록했다.

### 합격 기준과 기록 양식

IT-03 합격은 manifest 일치, 태그/HEAD/릴리스 노트 커밋 일치, 새 위치 오프라인 설치 성공,
clean 상태, 필수 단위시험 통과, S1 두 구성 PASS를 모두 만족해야 한다.
최종 납품 승인은 이 시험 외에도 PLAN의 필수 시나리오·그림·4분류 시험 보고·최종 PER-001 PASS가 필요하다.
LGPL·MPL 고지·소스 제공 의무 확인도 패키지 생성 성공과 구분한다.

| 기록 항목 | 기입 내용 |
|---|---|
| 시험 ID·일시·수행자 | IT-02-UT / IT-02-HW / IT-03, 날짜·시간대 |
| 버전·증거 | 태그·커밋·manifest, Actions run ID 또는 설치 기록 |
| 환경 | OS·Python·드라이버·SDK·도구 버전, 모델 스냅샷 식별자; 실제 경로는 비공개 기록 |
| 단계별 결과 | 명령, 종료 코드, 소요 시간, PASS/FAIL/미실행, 실패 원인 |
| 시험 수 | 통과·실패·skip 수, skip 조건 |
| 실측 결과 | B0/PDD의 run_status·analysis_status, 수집 완전성, 종료 확인 |
| 제외·한계 | 패키지의 대용량 제외 목록, not_collected 사유, 보안 예외 |
| 최종 판정 | 합격/불합격/미완료와 남은 조치 |
