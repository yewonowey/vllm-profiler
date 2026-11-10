# 단위시험 결과서

문서 갱신: 2026-11-11. 아래 시험·자료 확인일은 2026-11-10이다.

확인일: 2026-11-10. 기준 커밋 b824255의 코드이며 이번 작업은 문서만 변경했다.
[단위시험 계획서](unit_test_plan.md)의 메서드에 현재 추가된 연산 유형·그림·납품 시험을 포함한다.
실제 GPU/NPU 추론은 수행하지 않았다. RBLN 조건부 시험은 모듈 import,
도구 조건부 시험은 합성 trace/그림 생성이다.

## 실행 결과

| 환경·명령 | 전체 | 통과 | skip | 실패/오류 | 시간 |
|---|---:|---:|---:|---:|---:|
| 작업 저장소: python3 -m unittest discover -s tests/hetero | 44 | 44 | 0 | 0 | 14.667s |
| 작업 저장소: python3 -m unittest discover -s tests/pdd | 59 | 59 | 0 | 0 | 70.548s |
| IT-03 clone: tests/hetero | 44 | 44 | 0 | 0 | 14.987s |
| IT-03 clone: tests/pdd | 59 | 59 | 0 | 0 | 73.639s |
| IT-02 수동 Actions 재실행 | 44 | 41 | 3 | 0 | 2.655s |
| IT-02 push Actions | 44 | 41 | 3 | 0 | 1.968s |

로컬은 운영 환경 파일을 source했다. IT-03 clone의 hetero 재검사는 clone 외부에 설치한
도구 venv·바이너리를 명시했고 CUDA/RBLN 환경은 기존 것을 사용했다.
원문 로그는 로컬 전용 `.notes/delivery_unittest_{hetero,pdd}.txt`,
`.notes/delivery_it03_{hetero,pdd}.txt`다. 공개 납품 문서에는 경로 값을 옮기지 않는다.

## 모듈·계획 항목 대응

각 행의 개수는 테스트 메서드 수다. 표 안의 여러 입력 사례 수나 assert 수와 혼동하지 않는다.
메서드 이름의 test_ 접두사는 생략했다. 로컬에서는 아래 항목 모두 통과했다.

| 모듈 | 건수 | 실제 실행 메서드 | PLAN 요구사항·계획 항목 |
|---|---:|---|---|
| test_analysis.py | 3 | reproduction, synthetic_and_validation, join | SFR-002: 재현·원자료·ID 연결 |
| test_engine_events.py | 4 | flush_and_saved_step_times, time_based_flush, errors_off_and_copy_totals, rbln_imports | SFR-003: 엔진 이벤트·flush·import |
| test_loadgen.py | 2 | raw_records_routes_and_anchors, warmup_only | SFR-002: 원자료·라우팅·warmup |
| test_measurement.py | 7 | exclusive_phase_shares, boundary_deltas, attribution_and_union, energy_and_gates, classify_real_devices, validation, memory_bandwidth | SFR-002/003: 차분·귀속·에너지·게이트 |
| test_operators.py | 5 | npu_last_module_and_invalid_trace, types, aggregate, chrome_exports_and_finalize, pb | FT-OP-01: 합성 파싱·출력·무결성 게이트 |
| test_orchestrate.py | 3 | python_path_precedence, role_options, clean_repository | SFR-002/SER-009: 경로·역할·clean |
| test_overhead.py | 3 | statistics_and_decisions, cpu_and_retry, execution_and_failure_cleanup | PER-001: 통계·재시도·CPU·순서 |
| test_paths.py | 1 | no_absolute_filesystem_literals | SER-009 일부: 절대경로 검사 |
| test_profiler.py | 5 | options_routing_and_validation, expected_ids_and_span_wait, scrape, execution_and_failure_cleanup, trace_completion | SFR-002/003/QUR-003: 순서·정리·ID·로그 |
| test_release.py | 2 | release, workflow_yaml | IT-02/03 기반: 패키지 거부·구조·YAML |
| test_report_figures.py | 1 | synthetic_exports | FT-VIS-01: 합성 결과 그림 스모크 |
| test_smoke.py | 3 | streamed_token_count, proxy_selects_decoder_and_returns_target, real_fixtures_load_without_absolute_paths | 하네스 기반: SSE·proxy·fixture |
| test_sweep.py | 3 | pairs_cache_and_initial, resume_and_exports, kv_size_and_reorder | IT-01/FT-DS-01: 쌍·캐시·재개·결과표 |
| test_tools.py | 2 | required_tools_by_mode, scripts_reject_repository_paths | 설치·도구 모드·포트 회귀 |

## skip과 CI 해석

| 조건부 시험 | skip 조건 | 이번 로컬 / CI |
|---|---|---|
| engine_events.rbln_imports | RBLN_PY 미설정 | 통과 / skip |
| operators.pb | PDD_TOOLS_PY 또는 PERFETTO_TP_BIN 미설정 | 통과 / skip |
| report_figures.synthetic_exports | PDD_TOOLS_PY 미설정 | 통과 / skip |
| release.workflow_yaml | PyYAML 미설치 | 통과 / 통과 |

CI는 ubuntu-22.04/Python 3.10이며 prometheus_client·PyYAML·pre-commit을 설치한다.
실제 로그의 합계는 OK (skipped=3)이고 세 조건부 항목은 워크플로 환경·시험 decorator와 대응한다.
최초 수동 실행에서는 unittest가 성공했으나 actionlint의 SC1090으로 job이 실패했다.
환경 파일 source 지시문 주석을 추가한 b824255에서 단위시험과 pre-commit/actionlint가 모두 성공했다.

- [최초 실패 42816798675](https://github.com/yewonowey/vllm-profiler/actions/runs/42816798675)
- [수동 성공 42817562993](https://github.com/yewonowey/vllm-profiler/actions/runs/42817562993)
- [push 성공 42818113841](https://github.com/yewonowey/vllm-profiler/actions/runs/42818113841)

hetero_profile은 self-hosted 러너 미등록으로 미실행이다. 절차와 정적 검사로 갈음하며 HW CI 성공으로 적지 않는다.
UT의 합격 기준은 실행 assertion 전부 통과, 예상 외 실패·오류 0이다.
합성 장치 데이터와 import 성공은 SDK 시간 의미·실제 연산 무결성을 증명하지 않는다.
최종 측정·설치·미확인 항목은 [4분류 시험 보고](test_report.md)에서 구분한다.
