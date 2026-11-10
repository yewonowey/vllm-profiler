# 단위시험 계획서

기준일: 2026-11-10. 현재 tests/hetero의 14개 test 모듈, 44개 test 메서드를 대상으로 한다.
표의 요구사항 연결은 PLAN 2장 추적표와 시험의 실제 assertion에 근거한다.
UT 통과는 전체 FT/PT/IT 또는 실제 장치 성능 검증을 완료했다는 뜻이 아니다.
시험 파일의 줄 수는 wc -l로 측정했다. 코드·fixture를 이번 문서 작업에서 변경하지 않는다.

## 요구사항 대응

| PLAN 2장 요구사항 | 관련 구현 | 현재 UT/스모크 근거 | 별도 확인 |
|---|---|---|---|
| SFR-002 | 하네스·실행·클라이언트/서버 지표·결과표 | orchestrate/loadgen/profiler/analysis/measurement/sweep | FT-002-01~05 실제 시나리오, H0/H1/H4/H5 |
| SFR-003 | 엔진 이벤트·자원·에너지 | engine_events/measurement/profiler | FT-003-01~04, H2/H3/H4 실제 센서·시간 의미 |
| 하드웨어별 연산 특성 | opprofile/operator_stats | operators | FT-OP-01; 실제 장치 트랙 확인, decode 무결성·전체 prefill 미확인(H6b) |
| PCIe·GDDR6 병목 | transfer/resources | measurement의 게이트·T06·device ratio | FT-002-05; T03·T02·SDK 의미 미확인(H4/H5) |
| 프로파일링 데이터셋 | sweep/finalize | sweep/ operators의 내보내기 | FT-DS-01, IT-01 실제 전체 스윕 |
| PER-001 | overhead | overhead/tools | PER-001 1차·최종 측정 합격(test_report.md 참조); UT는 판정식 검증 |
| TER-001 | 전체 시험 | 본 UT 목록 | FT/PT/IT를 포함한 별도 4분류 보고 |
| QUR-003 | log_line | profiler 실행 로그를 smoke.assert_log_line로 검사 | FT-LOG-01 운영 로그 사례 |
| SER-009 | 경로·설치 안전장치 일부 | paths/tools/orchestrate의 제한 검사 | 보안 7분류·취약점 감사 전체를 대체하지 않음 |
| PMR-001 | 문서 세트 | 전용 UT 없음 | 문서 검토·납품 확인 |
| SW 소스·바이너리 납품 | 설치 스크립트 일부 | tools의 저장소 내부 경로 거부 | IT-03 실제 납품 패키지·오프라인 재설치 |

## 시험 환경과 실행

시스템 python3에서 전체 시험을 실행한다. 분석 모듈 import에 prometheus_client가 필요하다.
loadgen 시험은 토크나이저를 대체하며 실제 모델을 다운로드하지 않는다.
mock은 loopback 임의 포트, 파일·가짜 git 저장소·도구는 TemporaryDirectory를 사용한다.
실제 서버나 가속기 부하를 생성하지 않는다. 조건부 RBLN 시험도 모듈 import까지만 한다.

```bash
python3 -m unittest discover -s tests/hetero
python3 -m unittest discover -s tests/pdd
# 하나의 모듈만 확인할 때
python3 -m unittest tests.hetero.test_analysis
python3 -m unittest tests.hetero.test_measurement
```

| 조건 | 동작 | 결과 기록 |
|---|---|---|
| RBLN_PY 미설정 | test_engine_events.test_rbln_imports skip | RBLN 환경 import 미확인; HW 성공으로 세지 않음 |
| RBLN_PY 설정 | 지정 Python에서 엔진 세 모듈 import, timeout 120초 | SDK/venv 불일치는 오류이며 skip으로 숨기지 않음 |
| PDD_TOOLS_PY 또는 PERFETTO_TP_BIN 미설정 | test_operators.test_pb skip | PB 파서 실제 도구 연동 미확인 |
| 두 도구 변수 모두 설정 | 도구 Python의 TraceProtoBuilder로 합성 PB 생성, 실제 TP로 읽기 | 실제 RBLN PB 형식·장치 의미 확인과 별개(H6b) |
| loopback bind 제한 | HTTP 기반 시험은 실행 환경 오류 가능 | 허용된 환경에서 재실행; 시험 기대값 변경 금지 |

합격 기준은 실행된 모든 test assertion 통과, 예상 외 오류·실패 0이다.
조건부 skip 수와 이유를 별도 보고한다. tests/pdd 회귀와 변경·신규 pre-commit도 완료 조건이다.
수치별 허용오차는 아래와 같으며 전역 임의 완화는 하지 않는다.

## 모듈별 목록: 계산·상관·엔진

모든 메서드 이름에는 `test_` 접두사가 붙는다. 표에서는 그 접두사만 생략한다.

| 모듈 (줄 수) | 메서드 | 입력·기대 결과 | 요구사항 |
|---|---|---|---|
| test_analysis.py (115) | reproduction | real 네 workload의 요청·요약 중 옛 계산 필드와 공통인 모든 새 지표 비교; 상대오차 1e-9 | SFR-002 |
| 동일 | synthetic_and_validation | 손계산 세트별 요약·성공 수·PASS/FAILED, 입력/출력 검사, 파일 누락; 1토큰 TPOT/두 번째 지연 not_applicable | SFR-002 |
| 동일 | join | B0 세 장치/PDD decode0 쏠림, span 누락·중복, 엔진 suffix·형식 오류·종류별 중복 | SFR-002/003, H0 |
| test_measurement.py (164) | exclusive_phase_shares | 겹치고 W 밖으로 나간 합성 단계; 각 우선순위 값, 합=1, 기타≥0 | SFR-002 M14a |
| 동일 | boundary_deltas | 정상 평균, count=0, 음수 차분; 라벨별 리셋이 다른 증가에 가려지지 않음 | SFR-002 M06~M08 |
| 동일 | attribution_and_union | 시간가중 평균·최대·coverage 손계산, 긴 공백, 합집합, mixed/idle | SFR-003, M14b |
| 동일 | energy_and_gates | 에너지 120J, R11×R12≈1, 한 장치 결측 시 합계 없음, R09b>1 raw 보존, T03 미수집 | SFR-003, PCIe·GDDR6 |
| 동일 | classify_real_devices | 실제 all-smi 표본+합성 links; gpu_index를 바꿔도 UUID/PCI 대응 동일 | SFR-003 H2/H3 |
| 동일 | validation | 구간 10초에서 1개 성공 표본은 INCOMPLETE, 8개·경계 정상은 PASS | SFR-002/003 |
| 동일 | memory_bandwidth | 작은 모델·가중치 파일; device/span 분모 두 경우 T06/T07 손계산과 estimated/reason | PCIe·GDDR6 H4 |
| test_engine_events.py (116) | flush_and_saved_step_times | 256건·kv_layout/anchor 즉시 flush, merged 실행 합·시작끝, _record 저장 시각 사용 | SFR-003 WP4 |
| 동일 | time_based_flush | 가짜 monotonic으로 마지막 flush 후 1초 조건 | SFR-003 WP4 |
| 동일 | errors_off_and_copy_totals | 쓰기 불가 시 한 번 경고, 비활성 파일·타이머 없음, 두 그룹 누적·reset | SFR-003 WP4 |
| 동일 | rbln_imports | RBLN_PY에서 metrics_v2/model_runner/NIXL worker import | SFR-003, 조건부 |

measurement의 실수 계산은 assertAlmostEqual 또는 명시한 정확값 비교를 사용한다.
R09b 시험의 수학적 게이트 통과는 SDK total_device 의미를 검증하지 않는다.
엔진 비활성 복사 함수의 원본 AST 보존은 기존 WP4 diff 확인 사항이며,
현재 UT가 실제 장치 성능 무변화를 측정하는 것은 아니다.

## 모듈별 목록: 실행·입력·PER-001

| 모듈 (줄 수) | 메서드 | 입력·기대 결과 | 요구사항 |
|---|---|---|---|
| test_orchestrate.py (78) | python_path_precedence | CLI → 환경변수 → 오류의 우선순위 | SFR-002 WP1 |
| 동일 | role_options | 잘못된 키·개행·허용 안 된 인자·없는 역할 거부; 역할별 argv/env 반영 | SFR-002, SER-009 일부 |
| 동일 | clean_repository | 임시 git: 무시 파일 허용, 추적 변경 거부, compiler 불일치 거부 | SFR-002 H1 |
| test_loadgen.py (75) | raw_records_routes_and_anchors | 옛 원자료 키만 존재, 계산·summary 없음, B0 assigned_target/PDD 헤더, anchor 정수 필드 | SFR-002 |
| 동일 | warmup_only | 본측정 파일 없이 warmup_requests.jsonl만, HTTP 200 | SFR-002 |
| test_profiler.py (152) | options_routing_and_validation | 모드별 role env/args, B0 교차 슬롯·PDD 경로, workload 허용 키·이름·정수·예약어 검사 | SFR-002/003 |
| 동일 | expected_ids_and_span_wait | 실패 제외 기대 ID 집합; span 완료/누락과 trace_wait.json | SFR-002/003 H0 |
| 동일 | scrape | mock HTTP 200/404, 경계 JSONL의 시각·원문·label 필드 | SFR-003 |
| 동일 | execution_and_failure_cleanup | fake 정상/측정 예외 한 쌍, Collector 선행, service/ 생성 위임, 정리·wait·로그 형식 | SFR-002/003, QUR-003 |
| 동일 | trace_completion | 정상 gzip, 잘린 footer, 빈 파일, 파일 없음; 대기 결과·run.json 사유 | 연산자 수집 H6 |
| test_overhead.py (106) | statistics_and_decisions | OFF/ON 평균, 4블록 PASS/FAIL/ADD, 6블록 평균 판정·불확실성, 한 지표 FAIL 우선 | PER-001 |
| 동일 | cpu_and_retry | 가짜 stat의 단일/전체 코어 %, 재실행 통과/재실패 중단, 원본·재실행 8개 경로 보존 | PER-001 |
| 동일 | execution_and_failure_cleanup | warm-up 2회+최대6블록 순서, 서비스 start/stop 한 번, 단일 JSON 객체/목록, ABORTED 사유 | PER-001 |
| test_tools.py (80) | required_tools_by_mode | 모드별 필수 도구·고정 버전·누락, fake all-smi 같은 포트 재시작, SO_REUSEADDR | WP2, PER-001 회귀 |
| 동일 | scripts_reject_repository_paths | 번들 생성/설치 스크립트 각 1건 저장소 내부 경로 거부 | SER-009 일부, IT-03 기반 |

overhead CI 손계산은 mean=0.03, low≈−0.0003771, high≈0.0603771을
소수점 8자리로 비교한다. 임계값 5%의 경계는 표의 별도 사례로 확인한다.
UT 자체는 실제 monitor 부하가 5% 이하라는 증거가 아니다.
별도의 per001_r3 실측은 4블록에서 합격했다. 최종 코드 재측정 per001_final도 합격했다.

## 모듈별 목록: 결과표·연산자·기반

| 모듈 (줄 수) | 메서드 | 입력·기대 결과 | 요구사항 |
|---|---|---|---|
| test_sweep.py (158) | pairs_cache_and_initial | 요청 수·길이·seed·equal concurrency 불일치 거부; 캐시 조건/키 순서/deep 구분; initial 전체 쌍 검사 | SFR-002, IT-01 |
| 동일 | resume_and_exports | 성공 skip/실패 접미사, real fixture 칸, 비교율 100%·50%, 실패 행, dictionary·CSV, --only | 데이터셋 FT-DS-01 |
| 동일 | kv_size_and_reorder | KV 논리 512 bytes의 MiB 환산, 완전 토큰 맵 일치/누락 not_evaluated | SFR-002 S7, 데이터셋 |
| test_operators.py (160) | aggregate | 합성 kernel/cpu_op top N·호출 수·시간·카테고리 분모 비율 | 하드웨어별 연산 특성 |
| 동일 | chrome_exports_and_finalize | 합성 gzip, CUDA correlation으로 비동기 kernel 스텝 연결, CSV/MD 및 dataset 병합 | FT-OP-01/FT-DS-01 스모크 |
| 동일 | pb | 합성 PB 트랙·slice를 실제 Perfetto로 읽음 | FT-OP-01 기반, 조건부 |
| test_paths.py (17) | no_absolute_filesystem_literals | tools/hetero·tests/hetero의 지정 텍스트 확장자 경로 패턴 검사 | SER-009 일부 |
| test_smoke.py (98) | streamed_token_count | SSE 1요청에서 요청한 토큰 수 수신 | 부하 시험 기반 |
| 동일 | proxy_selects_decoder_and_returns_target | decoder 선택과 x-decode-target 응답 | PDD 시험 기반 |
| 동일 | real_fixtures_load_without_absolute_paths | real JSON/JSONL 16파일 로드, 사용자 절대경로 없음 | 재현 자료 기반 |

assert_log_line 헬퍼는 test_smoke.py에 있고 실제 log_line 연결 확인은
test_profiler.execution_and_failure_cleanup에서 수행한다. 별도의 test_logging.py는 없다.
test_paths는 docs/hetero를 순회하지 않는다. 문서의 경로 제약은 문서 검토에서 별도로 확인한다.

## HW로 남기는 항목과 증거 한계

| 항목 | 현재 대체·보완 근거 | 상태 |
|---|---|---|
| mock의 모든 지연·실패·SSE 세부 조합 | 최소 3개 스모크, loadgen 원자료 시험 | 상세 시험 생략(HW 확인으로 대체); 다른 서버 버전 형식 미확인(H0) |
| 실제 copy_ 동기성, device·문맥·KV 그룹 의미 | H0/H4/H6 메모와 이벤트 UT | 미확인(H4); synthetic 성공으로 승격 금지 |
| all-smi 센서·UUID/PCI·링크·장시간 안정성 | real 표본 대응 시험, S1/S2 실측 | 라벨 대응 확인; 장시간/센서 주기 미확인(H2), 실효 링크 성능 미확인(H3) |
| NIXL 전송 count 단위·실제 TLS | 경계 차분 시험, H5 메모 | 미확인(H5); 요청 수 일치는 필요 근거지만 일반 전송 단위 확정 아님 |
| 온라인 deep export 및 오프라인 NPU PB | gzip·합성 PB 스모크 | HW 재확인 필요(H6), 장치 트랙 확인, 정상 전체 측정 집계 미확인(H6b) |
| 캐시·4B | cache key UT, H7 기동·반복 관찰 | 조건 전반 캐시 호환성 미확인(H7) |
| PER-001 판정 | per001_r3 원본 결과와 `.notes/PER001_1차_2026-11-07.md` | PER-001 1차·최종 측정 합격(test_report.md 참조); 최종 측정 per001_final PASS |

정합성 원본 파일의 생산 규약(IT-01), CI 전체(IT-02), 납품 설치(IT-03),
보안 점검 및 최종 시각화 산출물은 이 UT 목록만으로 완료 판정하지 않는다.
회귀 시험의 상세 보고는 실제 실행 날짜·명령·통과/skip 수를 기록한 시험 보고서에서 관리한다.

## 추가·갱신된 시험(2026-11-10)

| 모듈 | 추가 메서드 | 요구사항·범위 |
|---|---|---|
| test_operators.py | npu_last_module_and_invalid_trace, types | H6b 선택·오류 게이트, 유형 분류 합성 사례 |
| test_report_figures.py (89줄) | synthetic_exports | FT-VIS-01, 합성 자료에서 그림 생성 스모크; PDD_TOOLS_PY 없으면 skip |
| test_release.py (72줄) | release, workflow_yaml | IT-03 거부 조건·구조·해시·제외 규칙, IT-02 YAML; PyYAML 없으면 YAML만 skip |

현재 실행 결과는 [단위시험 결과서](unit_test_report.md), 실제 HW·CI·설치 판정은 [시험 보고](test_report.md)를 따른다.
