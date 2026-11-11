# 단위·시스템·성능·통합 시험 결과서

문서 갱신: 2026-11-11. UT·IT-03 확인일은 2026-11-10, sweep3 갱신 확인일은 2026-11-11이다.

갱신일: 2026-11-11. PLAN v6.2 WP14의 UT/FT/PT/IT 분류를 따른다.
`<결과>`는 실측 결과 루트, `<IT03>`는 독립 설치 루트다. 파일명은 각 루트 기준 상대 경로다.
수치는 기존 결과 파일에서 직접 읽거나 명시한 식으로 계산했다. 이번 문서 작업에서 서버를 다시 실행하지 않았다.
PASS는 해당 검사 범위의 판정이며 성능 우위·전체 출력 정합성·미수집 지표의 검증을 뜻하지 않는다.

## 1. 단위시험(UT)

작업 저장소 hetero 44/44, 기존 pdd 59/59 통과, skip·실패·오류 0.
IT-03 clone에서도 같은 수의 시험을 통과했다. 메서드별 대응·로그·조건부 skip은
[단위시험 결과서](unit_test_report.md)에 있다. 시험 코드와 기대값을 이번 작업에서 변경하지 않았다.

## 2. 시스템·기능시험(FT)

근거: `<결과>/sweep3/results.csv`, `runs/<scenario>/<workload>/profile/summary.json`.
28/28 시나리오, 36/36 workload에서 run_status와 analysis_status는 모두 PASS다.
아래는 성공 상태와 별도로 목표 시간·출력 동일성·미수집 제약을 남긴 판정이다.

| 시험 ID | 시나리오·자료 | 결과 | 판정·제약 |
|---|---|---|---|
| FT-002-01 | S1·S2 B0/PDD, 4행 | 원자료·계측 PASS | 기능 합격. capacity 비교이며 동일 동시성 비교와 구분 |
| FT-002-02 | S3a 배치1/2/4, S3b 동시성2/4/8, 12행 | 모두 PASS | 배치8 B0 실패로 제외. 일부 B0 30초 미달 |
| FT-002-03 | S4 Qwen3-0.6B/4B B0/PDD, 4행 | 모두 PASS | 모델 크기 관측; 반복 측정 통계 아님 |
| FT-002-04 | S5 B0/PDD 6행·S5t PDD trace 3행 | 모두 PASS | D2 입출력 길이비 대체; 물리적 분할 비율 조절 아님 |
| FT-002-05 | S5t·H0의 단계/전송, transfer·memory_bw | 산출·게이트 확인 | 부분 확인: T03·R09b 미수집, NPU T06 하한 추정 |
| FT-003-01 | phase_resources의 CPU·시스템 메모리 | 수집·시간가중 귀속 | 추정, 표본 coverage와 혼합 상태 확인 필요 |
| FT-003-02 | GPU 활용률·전력·메모리, links | UUID 대응 확인 | 계측 PASS와 이론 링크 속도 달성은 별개 |
| FT-003-03 | NPU0/NPU1 자원·PCI 대응 | 양 장치 표본 확인 | 보드 GDDR6·호스트 메모리를 구분 |
| FT-003-04 | S6 prefill/decode 우세 B0/PDD, 4행 | 모두 PASS | prefill 우세의 두 구성은 목표120초 미달 |
| FT-002-05 보완 | S7 reorder 0/1, 2행 | 측정 PASS, 출력 정합성 FAIL(결함 보고) | monitor r1↔trace r1 16/16, r0와0/16. 계측 영향 배제, 공통 reorder 경로 결함 |
| PT-002 연계 | S8 PDD trace, 1행 | PASS | trace 부하 참고치, PER-001 판정과 분리 |
| FT-OP-01 | h6b/*/operators.csv·diagnostics.json | GPU 두 phase 집계, NPU prefill 부분 집계 | 부분 확인. NPU decode 64/256토큰 무결성 문제로 미수집 |
| FT-DS-01 | sweep3/dataset, results·comparison | CSV·사전 생성 | 생성 확인. 일반 정합성은 not_evaluated, S7만 토큰 비교 |
| FT-VIS-01 | sweep3/figures 및 보고서 그림 | 그림 생성·스모크 통과 | 그래프가 통계적 유의성을 추가 입증하지 않음 |
| FT-LOG-01 | run.json·service/logs, profiler 로그 형식 시험 | 단계 성공/실패·정리 로그 확인 | 모든 운영 장애의 로그 완전성은 미시험 |

### 재측정 대상 목표 시간 확인

| 시나리오 / workload | 실제 요청 수 | 현재 initial 요청 수 | 시간(s) | 목표(s) | 판정 |
|---|---:|---:|---:|---:|---|
| s3a_b4_b0 / i2048_o256 | 32 | 48 | 23.526 | 30 | 미달 |
| s3a_b4_pdd / i2048_o256 | 32 | 48 | 85.923 | 30 | 충족 |
| s3b_c4_b0 / i2048_o256 | 32 | 48 | 25.908 | 30 | 미달 |
| s3b_c4_pdd / i2048_o256 | 32 | 48 | 125.260 | 30 | 충족 |
| s3b_c8_b0 / i2048_o256 | 32 | 64 | 19.923 | 30 | 미달 |
| s3b_c8_pdd / i2048_o256 | 32 | 64 | 85.772 | 30 | 충족 |
| s6_b0 / i4096_o1 | 280 | 512 | 66.623 | 120 | 미달 |
| s6_b0 / i32_o4096 | 16 | 16 | 321.237 | 120 | 충족 |
| s6_pdd / i4096_o1 | 280 | 512 | 117.064 | 120 | 미달 |
| s6_pdd / i32_o4096 | 16 | 16 | 637.548 | 120 | 충족 |

재실행한8개 시나리오 중 전체 workload가 목표를 충족한 것은3개, 미달 workload가 있는 것은5개다.
요청 수 상향(48/48/64/512)이 실제 실행에 적용되지 않았다. 자료는 여전히32/280이다.
28/28 측정PASS를 목표 시간 충족·출력 정합성 합격으로 바꾸지 않는다.
적용한 시나리오 파일과 입력 스냅샷을 확인한 뒤 재실행하거나 예외를 명시적으로 승인해야 한다.

### H0 요청 연결

근거: h0_trace/h0/profile/summary.json, otel/traces.jsonl, rbln_metrics의 events.
현재 요약은 run_status=PASS, analysis_status=INCOMPLETE다.
prefill span 4개, decode0/1 각각 span·kv_xfer_start·kv_xfer_done·kv_h2d 2개씩 연결됐고
누락·중복·unexpected·unmatched는 모두 0이다. ID 연결은 합격이다.
각 endpoint의 본측정 표본이 1개로 최소2개에 미달해 계측 전체는 INCOMPLETE다.
과거 WP7a의 매칭 PASS와 이후 WP7b 계측 판정을 혼동하지 않는다.
OTEL은 cmpl-<client ID>-0, 엔진은 그 뒤 16진수8자리 접미사다.
엔진 suffix를 정규식 전체 일치로 제거하는 수정으로 최초 KV 매칭 실패를 해결했다.

## 3. 성능시험(PT)

### PT-001 / PER-001

S2 PDD, 서비스 none, i4096/o256·16요청·동시성8·seed20260924·warmup1.
각 측정은 워밍업 OFF/ON 두 번 뒤 OFF·ON·ON·OFF 4블록을 수행했다.
유효 실행 18/18(본측정16), 추가2블록 불필요. 두 지표의 90% 양측 t 신뢰구간 상한≤5%로 합격했다.
부호는 d_tp=(OFF−ON)/OFF, d_lat=(ON−OFF)/OFF다. 표는 모두 % 단위다.

| 측정 | 커밋 | d_tp 평균 [90% CI] | d_lat 평균 [90% CI] | p95 E2E 범위(s) | 판정 |
|---|---|---|---|---|---|
| 1차 (per001_r3) | b776289 | -0.049765 [-0.182904, +0.083374] | -0.037643 [-0.105786, +0.030500] | 65.572557–65.794617 | PASS |
| 최종 (per001_final) | 3a6ff3d | +0.139838 [+0.034939, +0.244737] | +0.114780 [+0.050106, +0.179455] | 65.742182–66.002782 | PASS |

출처: 각 per001*/overhead/overhead.json의 decisions·blocks·runs,
service/config.json의 environment.commit. p95 범위는 워밍업 두 실행을 제외한 본측정16회의 범위다.
최종 측정 커밋은 **3a6ff3dcfce1621706d8913210175b344ab6bfdb**다.
이후 b824255까지 측정 경로의 run.py·scrape.py·overhead.py는 보안 근거/nosec 주석만 바뀌었다.
하네스·분석·엔진을 포함해 대조한 19개 Python 파일의 AST는 동일했고 나머지16개는 텍스트도 동일했다.
이는 위 코드 범위의 동작 변경이 없다는 근거이며, 임의의 향후 코드·SDK 변경에 대한 보증은 아니다.

첫 시도 per001_r1b는 연속 ON의 포트 사전 bind에서 ABORTED,
per001_r2는 dirty 작업 트리로 기동 실패했다. SO_REUSEADDR·대기/종료 확인과 clean worktree로 조치했다.
실패 실행을 합격 표본에 넣지 않았다. 근거는 해당 overhead 자료와 PER001 1차 메모다.

### PT-002 trace 모드 참고치

출처: s2_pdd/s2, s8_r1/s2, s8_r2/s2의 profile/summary.json.
차이=100×(trace/monitor−1). 같은 S2 조건의 관측값이며 ABBA나 반복 통계 검정이 아니다.

| 실행 | 처리량(token/s) | monitor 대비(%) | 평균 E2E(s) | monitor 대비(%) |
|---|---:|---:|---:|---:|
| s2_pdd | 62.440595 | +0.000 | 48.757362 | +0.000 |
| s8_r1 | 62.379868 | -0.097 | 48.824239 | +0.137 |
| s8_r2 | 62.529383 | +0.142 | 48.626938 | -0.267 |

판정: 참고 측정 완료. 작은 부호 차이의 원인을 trace 자체의 성능 개선/저하로 단정하지 않는다.

## 4. 통합시험(IT)

| 항목 | 근거 | 판정 |
|---|---|---|
| IT-01 스윕 | sweep3/scenarios.json, results.csv 36행, comparison.csv, dataset | 28/28 시나리오 PASS, 표·데이터셋 생성 확인. S7 출력 정합성·시간 목표는 미충족 |
| IT-02 일반 CI | 수동 Actions 42817562993, push 42818113841; b824255 | 합격: 44건 중41통과·3skip, pre-commit/actionlint 통과 |
| IT-02 최초 시도 | Actions 42816798675 | SC1090 실패; source 지시문 주석 추가 후 해결 |
| IT-02 self-hosted | 러너 미등록(수행자 확인) | 미실행. 합의대로 절차 문서화·actionlint로 갈음; HW 실행·artifact 실증은 남음 |
| IT-03 rc1 설치 | MANIFEST·clone·설치물·단위시험·S1 결과 직접 재확인 | 아래 범위 합격 |

Actions 링크·시험 수는 [단위시험 결과서](unit_test_report.md), 재실행 순서는 [시험 절차](test_procedure.md)에 있다.

### IT-03 판정과 S1 재현

v1.0.0-rc1 패키지 MANIFEST 검사 종료코드0, clone HEAD·태그 커밋 b824255… 일치,
git status --porcelain 빈 출력이다. 도구 venv의 고정 패키지 설치물도 직접 조회했다.
설치 명령 자체의 과거 실행은 수행자 확인이며 이번에는 재설치하지 않았다.
clone 단위시험 hetero44·pdd59건 모두 통과. S1 B0·PDD run.json 단계 모두 성공,
각 summary의 run_status·analysis_status 모두 PASS, results.csv 2행·comparison.csv 1행 생성.

설정: Qwen3-0.6B FP16, ctx1024, batch1, block_size128, blocks32,
i512/o128·176요청·seed20260924, B0 슬롯1/1/1, PDD 동시성2.
출처: 양 실행의 service/config.json 및 workload/config.json. 실행별 포트는 다르다.

비교 출처: <결과>/sweep2/results.csv와 <IT03>/s1_sweep/results.csv.
차이=100×(IT-03/sweep2−1), 각 지표 ±10% 이내가 합격 기준이다.

| 구성 | 지표 | sweep2 | IT-03 | 차이(%) |
|---|---|---:|---:|---:|
| s1_b0 | 처리량(token/s) | 746.760654 | 741.233603 | -0.740 |
| s1_b0 | makespan(s) | 30.167631 | 30.392578 | +0.746 |
| s1_b0 | 평균 TTFT(s) | 14.734066 | 15.028929 | +2.001 |
| s1_b0 | 평균 TPOT(s) | 0.003681 | 0.003713 | +0.849 |
| s1_b0 | 평균 E2E(s) | 15.201708 | 15.500538 | +1.966 |
| s1_pdd | 처리량(token/s) | 157.038075 | 156.998632 | -0.025 |
| s1_pdd | makespan(s) | 143.455656 | 143.491696 | +0.025 |
| s1_pdd | 평균 TTFT(s) | 71.541247 | 71.578783 | +0.052 |
| s1_pdd | 평균 TPOT(s) | 0.010664 | 0.010725 | +0.579 |
| s1_pdd | 평균 E2E(s) | 72.895796 | 72.941170 | +0.062 |


**IT-03 합격:** 10개 지표 모두 허용범위, 최대 절대 차이 2.001230%.
동일 서버에서 독립 clone·도구 설치를 검증한 결과이며 다른 장비의 호환성 검증은 아니다.
근거 세부 기록은 로컬 전용 .notes/IT03_2026-11-10.md다.

## 남은 확인과 납품 판단

| 항목 | 남은 확인 |
|---|---|
| H4 | copy_ 동기 여부, SDK device 시간 의미; T03/R09b 미수집 유지, NPU T06 하한 추정 |
| H5 | NIXL count의 일반 전송 단위·실제 TLS 경로; 특정 요청수 일치만으로 확정하지 않음 |
| H6b | NPU decode 무결성 복구·prefill 전체 집계, GPU T06 접근량 모델 |
| H7 | SDK/모델 조건 전반 캐시 호환성 |
| IT-02-HW | 러너 등록 후 실제 프로파일·정리·artifact 확인 |
| S7·시간 기준 | monitor 대조로 계측 영향 배제. 공통 reorder 결함 수정과 요청 상향 적용 재측정 |
| 배포 범위 | 본 문서 갱신은 rc1 이후이므로 최종 태그 패키지에 포함됐는지 별도 확인 |

PT-001 최종과 IT-03은 합격이다. 모든 FT의 모든 수치·정확도가 검증됐다는 포괄 판정은 하지 않는다.
보안·라이선스 잔여 항목은 해당 점검표에서 관리한다.

IT-03의 위 표는 rc1 설치 당시 sweep2 기준의 역사적 비교다. sweep3 수치로 바꾸어 과거 설치 판정을 재작성하지 않았다.
rc1 이후 HEAD에는 문서 변경만 있고 측정·설치 코드 변경은 없다. S1 성능 재실행은 필요 없으나,
최종 태그·패키지의 MANIFEST·HEAD·문서·dataset·그림·설치/단위시험 검사는 다시 수행해야 한다.
