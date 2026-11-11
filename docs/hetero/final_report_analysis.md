# 최종보고서 분석 장

갱신일: 2026-11-11. 온라인 결과는 sweep3를 기준으로 재집계했다. 원본 trace·엔진 코드는 변경하지 않았다.
**주요 관찰:** 유효 비교15쌍에서 PDD 처리량은 B0보다 42.69~85.39% 낮았고,
출력 토큰당 가속기 에너지는 34.31~277.84% 높았다(추정).
출처: sweep3/comparison.csv·dataset/energy.csv. 제한된 구성의 관측이며 일반적인 제품 우열 판정이 아니다.

## 1. 시험 환경과 방법

경로는 외부 `<결과 루트>` 기준이다. R01~R36은 부록의 scenario/workload/source_summary를 뜻한다.
각 R의 서비스 설정은 같은 run의 service/config.json, 입력 설정은 workload/config.json이다.
로컬 근거 표는 .notes/results_summary_2026-11-11.md, 이전 수치 대비 목록은 .notes/sweep3_number_changes_2026-11-11.md다.

sweep3의 **28/28 시나리오, 36/36 workload가 run_status·analysis_status PASS**다.
S7은 측정 PASS와 출력 정합성 FAIL을 구분한다. 접미사 attempt를 독립 반복 통계로 합치지 않는다.
dataset 행 수: energy.csv 144, memory_bw.csv 108, operators.csv 121, operators_by_type.csv 23, phase_resources.csv 1,671, requests.csv 2,768, resource_timeseries.csv 81,642, runs.csv 36, transfer.csv 108 (독립 실험 수 아님).

| 항목 | 설정·근거 |
|---|---|
| GPU | NVIDIA RTX PRO 6000 Blackwell Workstation Edition 1장, 96GB GDDR7; PLAN1장·links.json |
| NPU | RBLN-CA22 2장, 각16GB GDDR6; PLAN1장·links.json |
| 링크 | GPU 최대 Gen5×16, NPU 32.0GT/s×16; 규격이며 실효 대역폭 아님 |
| 소프트웨어 | vLLM CUDA0.22.0/RBLN0.22.0+cpu, compiler0.11.1.post2.dev2+g2995098f.prod; 각 service/config.json |
| 코드 | 63ae889a8edc92ebccf9d15fcd2a66d108ac2dac; sweep3의 모든 service/config.json environment.commit |
| 도구 고정 | all-smi0.28.1, Collector0.163.2, Perfetto58.2/Python0.58.2, matplotlib3.10.9; versions.env |

B0는 각 장치 전체 추론, PDD는 GPU prefill+NPU decoder 두 대다.
capacity는 장치별 배치 용량, equal_concurrency(S3b)는 전체 슬롯 수를 맞춘 비교다.
S3b 동시성2/4/8의 B0 슬롯은 (1,1,0)/(2,1,1)/(3,3,2)이며 동시성2에서는 NPU1 요청이 없다.
모델·길이·요청 수·배치는 다음 표의 실제 실행값이다. 새 initial.json 계획값을 실측값으로 바꾸어 쓰지 않는다.

| 시나리오 | 모델·dtype | i/o | 실제 요청 수 | 배치/blocks | 모드 |
|---|---|---|---|---|---|
| S1 | Qwen3-0.6B FP16 | 512/128 | 176 | 1/32, ctx1024 | monitor |
| S2 | Qwen2.5-3B BF16 | 4096/256 | 16 | 4/160 | monitor |
| S3a | Qwen2.5-3B BF16 | 2048/256 | 32 | 1/2/4, blocks40/80/160 | monitor |
| S3b | Qwen2.5-3B BF16 | 2048/256 | 32 | 4/160, 동시성2/4/8 | monitor |
| S4 | Qwen3-0.6B·4B FP16 | 2048/256 | 304 | 4/160 | monitor |
| S5·S5t | Qwen2.5-3B BF16 | 4096/256,2176/2176,256/4096 | 각16 | 4/160 | monitor·trace |
| S6 | Qwen2.5-3B BF16 | 4096/1,32/4096 | 280,16 | 4/160 | monitor |
| S7·S8 | Qwen2.5-3B BF16 | 4096/256 | 각16 | 4/160 | trace |

S1 외 ctx4352, block_size·max_num_batched_tokens128, seed20260924다(R01~R36).
warm-up을 분리하며 makespan은 첫 예정 도착~마지막 완료, 처리량은 성공 출력토큰/makespan이다.
TTFT·E2E는 클라이언트 큐 포함, TPOT는 요청별(마지막−첫 출력)/(출력수−1), 백분위는 nearest-rank다.
monitor 단계 귀속은 추정, trace는 span·이벤트를 clock anchor로 MONOTONIC에 대응한다.
서버 ID는 cmpl-<client ID>-0, 엔진은 끝의16진수8자리 접미사를 제거한다. 세부 정의는 metrics_definition.md.

### 재측정 대상 지속시간

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

8개 시나리오의10개 workload 중5개가 목표 시간 미달이다. S3 48/48/64·S6 prefill512 요청 상향은
현재 initial.json에만 있고 실행 자료는32·280이다. 전체 PASS를 시간 목표 충족으로 해석하지 않는다.
요청 상향을 적용한 재실행 또는 목표 미달 예외 승인이 필요하다.

H6b는 오프라인 단일 장치 LLM API로 warm-up 뒤 prefill4096/1·decode32/256 각4요청을 수집했다.
NPU decode는64토큰도 재측정했으나 무결성 문제로 미수집이다(meta.json과 H6b 메모). 장치 추론 성공과 trace 정상은 별개다.

![구성과 측정 경계](figures/01_design.png)

그림1. 출처: PLAN5.3·5.4. 설계도이며 실측 수치 아님.

## 2. B0 대 PDD 지연·처리량

처리량 변화=(PDD/B0−1)×100, makespan 감소=(1−PDD/B0)×100. 출처: 각R 및 sweep3/comparison.csv.

| 조건/i/o | 처리량 B0→PDD(token/s) | 변화(%) | makespan B0→PDD(s) | 감소(%) | 출처 |
|---|---|---:|---|---:|---|
| s1/i512_o128 | 745.721 → 159.163 | -78.66 | 30.210 → 141.540 | -368.53 | R01,R02 |
| s2/i4096_o256 | 109.010 → 62.330 | -42.82 | 37.575 → 65.714 | -74.89 | R03,R04 |
| s3a_b1/i2048_o256 | 175.421 → 44.807 | -74.46 | 46.699 → 182.828 | -291.50 | R05,R06 |
| s3a_b4/i2048_o256 | 348.212 → 95.341 | -72.62 | 23.526 → 85.923 | -265.23 | R07,R08 |
| s3a_b2/i2048_o256 | 261.800 → 69.334 | -73.52 | 31.291 → 118.152 | -277.59 | R09,R10 |
| s3b_c2/i2048_o256 | 157.429 → 40.282 | -74.41 | 52.036 → 203.365 | -290.81 | R11,R12 |
| s3b_c4/i2048_o256 | 316.194 → 65.400 | -79.32 | 25.908 → 125.260 | -383.48 | R13,R14 |
| s3b_c8/i2048_o256 | 411.192 → 95.509 | -76.77 | 19.923 → 85.772 | -330.53 | R15,R16 |
| s4_qwen3-0.6b/i2048_o256 | 934.789 → 136.611 | -85.39 | 83.253 → 569.677 | -584.27 | R17,R18 |
| s4_qwen3-4b/i2048_o256 | 461.627 → 77.318 | -83.25 | 168.586 → 1006.550 | -497.05 | R19,R20 |
| s5/i4096_o256 | 109.061 → 62.501 | -42.69 | 37.557 → 65.535 | -74.49 | R21,R24 |
| s5/i2176_o2176 | 154.237 → 78.290 | -49.24 | 225.731 → 444.703 | -97.01 | R22,R25 |
| s5/i256_o4096 | 192.597 → 97.195 | -49.53 | 340.276 → 674.276 | -98.16 | R23,R26 |
| s6/i4096_o1 | 4.203 → 2.392 | -43.09 | 66.623 → 117.064 | -75.71 | R30,R32 |
| s6/i32_o4096 | 204.012 → 102.794 | -49.61 | 321.237 → 637.548 | -98.47 | R31,R33 |

| 조건/i/o | 평균 TTFT B0→PDD(s) | 평균 TPOT(s) | 평균 E2E(s) | p95 E2E(s) | 출처 |
|---|---|---|---|---|---|
| s1/i512_o128 | 14.814 → 70.762 | 0.004 → 0.011 | 15.283 → 72.100 | 28.794 → 135.217 | R01,R02 |
| s2/i4096_o256 | 3.119 → 18.475 | 0.069 → 0.118 | 20.632 → 48.639 | 37.575 → 65.714 | R03,R04 |
| s3a_b1/i2048_o256 | 17.176 → 86.277 | 0.013 → 0.043 | 20.549 → 97.154 | 36.098 → 182.558 | R05,R06 |
| s3a_b4/i2048_o256 | 4.204 → 33.225 | 0.026 → 0.080 | 10.781 → 53.632 | 23.526 → 85.739 | R07,R08 |
| s3a_b2/i2048_o256 | 9.154 → 52.302 | 0.018 → 0.055 | 13.838 → 66.331 | 31.291 → 117.925 | R09,R10 |
| s3b_c2/i2048_o256 | 19.589 → 95.945 | 0.010 → 0.048 | 22.225 → 108.110 | 40.014 → 203.029 | R11,R12 |
| s3b_c4/i2048_o256 | 10.362 → 55.426 | 0.011 → 0.058 | 13.126 → 70.328 | 25.908 → 124.942 | R13,R14 |
| s3b_c8/i2048_o256 | 6.318 → 33.137 | 0.015 → 0.080 | 10.267 → 53.502 | 19.922 → 85.594 | R15,R16 |
| s4_qwen3-0.6b/i2048_o256 | 34.221 → 280.823 | 0.011 → 0.052 | 36.902 → 293.965 | 69.369 → 549.128 | R17,R18 |
| s4_qwen3-4b/i2048_o256 | 69.725 → 493.108 | 0.021 → 0.096 | 75.104 → 517.687 | 140.364 → 967.309 | R19,R20 |
| s5/i4096_o256 | 3.142 → 18.371 | 0.069 → 0.119 | 20.655 → 48.662 | 37.557 → 65.535 | R21,R24 |
| s5/i2176_o2176 | 4.393 → 112.304 | 0.054 → 0.101 | 122.322 → 332.978 | 225.731 → 444.703 | R22,R25 |
| s5/i256_o4096 | 5.782 → 168.806 | 0.044 → 0.082 | 186.986 → 505.501 | 340.276 → 674.276 | R23,R26 |
| s6/i4096_o1 | 31.887 → 59.107 | 미수집 → 미수집 | 31.888 → 59.107 | 59.845 → 111.299 | R30,R32 |
| s6/i32_o4096 | 5.667 → 159.585 | 0.042 → 0.078 | 177.338 → 478.059 | 321.237 → 637.548 | R31,R33 |

PDD 처리량 우세는 관측되지 않았다. 동일 동시성 S3b도 같은 방향이지만 특정 역할·모델·유한 부하의 결과다.
출력1토큰 TPOT는 미수집이며0이 아니다.
R02 평균 TTFT 70.762초 중 큐 70.492초, send기준 service TTFT 0.270초다.
R26 평균 TTFT 168.806초 중 큐 168.517초, send기준 service TTFT 0.289초다.
따라서 예정 도착 기준 TTFT 전체를 GPU prefill 연산 지연으로 부르지 않는다.

9월 기준 비교(SEP 출처는 부록):

| 조건 | 9월 token/s | sweep3 token/s | 차이(%) | 출처 |
|---|---:|---:|---:|---|
| s1_b0 | 543.519 | 745.721 | +37.20 | SEP1-B,R01 |
| s1_pdd | 154.745 | 159.163 | +2.85 | SEP1-P,R02 |
| s2_b0 | 109.318 | 109.010 | -0.28 | SEP2-B,R03 |
| s2_pdd | 62.245 | 62.330 | +0.14 | SEP2-P,R04 |

S1은9월18요청과 현재176요청이 달라 직접 재현 판정하지 않는다. S2는16요청이다.

![B0 대 PDD 성능](figures/02_comparison.png)

그림2. 출처: sweep3/results.csv·comparison.csv. measured, 단일 선택 실행.

## 3. 모델 크기·배치·동시성 영향

배치1→2→4: B0 175.421 → 261.800 → 348.212; PDD 44.807 → 69.334 → 95.341 token/s (각 해당 R).
동시성2→4→8: B0 157.429 → 316.194 → 411.192; PDD 40.282 → 65.400 → 95.509 token/s (각 해당 R).
모델0.6B→4B: B0 934.789 → 461.627; PDD 136.611 → 77.318 token/s (각 해당 R).
배치·슬롯·blocks가 함께 변하므로 순수 커널 효율의 인과 효과로 분리하지 않는다.
S3 일부는 목표30초 미달이다. S4 결과도 반복 통계가 아니므로 모델 크기만으로 차이를 일반화하지 않는다.
B0 배치8은 Triton 샘플러의 미구현 num_compute_units로 실패했고 PDD decode 전용은 성공했다.
쌍이 없는 배치8을 비교표에 넣지 않는다(개발팀 보고 사항; sweep1 s3a_b8_b0/service/logs/npu0.log).

![배치·동시성·모델 크기](figures/03_scaling.png)

그림3. 출처: sweep3/results.csv S3a·S3b·S4. measured; 일부 목표 시간 미달.

## 4. 분할 비율 대체 분석(D2): S5·S5t

입출력 합4352의 길이비 변화이며 물리적 레이어/연산량 분할률이 아니다.
M14a는 요청 [send,completed]를 decode>layout>KV>prefill>큐 순서로 배타 분할한다. 기타는 미배정 구간이다.
M06~M10 원 경과시간은 겹침을 허용한 별도 값이다. 아래 M14a는 요청별 평균 %, 출처R27~R29.

| S5t | P큐 | P prefill | KV | layout | D큐 | decode | 기타 |
|---|---:|---:|---:|---:|---:|---:|---:|
| i4096_o256 | 2.151 | 1.306 | 1.209 | 0.955 | 0.134 | 93.817 | 0.426 |
| i2176_o2176 | 0.168 | 0.099 | 0.093 | 0.084 | 0.016 | 99.493 | 0.047 |
| i256_o4096 | 0.013 | 0.011 | 0.016 | 0.016 | 0.008 | 99.911 | 0.024 |

M14b는 장치별 각 단계 구간의 합집합/본측정 구간이며 단계끼리 겹친다. 값은 %, 출처 동일.

| S5t | GPU prefill | NPU0 KV/layout/decode | NPU1 KV/layout/decode |
|---|---:|---|---|
| i4096_o256 | 10.083 | 4.739 / 3.979 / 97.972 | 4.767 / 3.540 / 97.951 |
| i2176_o2176 | 0.763 | 0.362 / 0.350 / 99.818 | 0.382 / 0.320 / 99.824 |
| i256_o4096 | 0.065 | 0.065 / 0.066 / 99.977 | 0.065 / 0.063 / 99.973 |

monitor M14a는 first_token/after_first_token 근사이고 M14b도 클라이언트 구간 기반 추정이다.
긴 출력의 decode 비중은 크지만 연산 포화·메모리 병목을 단정하지 않는다.

![S5·S5t 단계 비율](figures/04_phases.png)

그림4. 출처: sweep3/results.csv S5·S5t. monitor estimated, trace measured; 단계 중첩 주의.

## 5. 단계별 자원 활용률

GPU UUID·NPU PCI를 links.json에 대응한다. 장치 지표는 장치 상태, CPU·메모리는 시스템 상태로 시간가중 귀속한다.
아래 평균은 모두 추정이며 메모리는 GiB(2^30 bytes), 전력W·활용률%다. 출처각R.phase_resources.

| 조건/상태 | GPU 활용/전력/메모리 | NPU0 활용/전력/메모리 | NPU1 활용/전력/메모리 | CPU% / 시스템 GiB |
|---|---|---|---|---|
| R03 s2_b0/all | 11.97 / 105.75 / 7.41 | 92.42 / 50.96 / 6.82 | 90.99 / 50.45 / 6.82 | 4.97 / 23.64 |
| R04 s2_pdd/all | 5.39 / 90.55 / 7.41 | 88.93 / 46.72 / 6.82 | 88.80 / 45.95 / 6.82 | 10.83 / 25.26 |

| 조건/장치/상태 | 활용률% | 전력W | coverage% |
|---|---:|---:|---:|
| R03/gpu/decode | 82.79 | 341.98 | 100.000 |
| R03/npu0/decode | 95.61 | 49.63 | 99.378 |
| R03/npu1/decode | 95.69 | 49.19 | 99.377 |
| R04/gpu/prefill | 30.05 | 193.34 | 96.300 |
| R04/npu0/decode | 89.73 | 46.80 | 100.000 |
| R04/npu1/decode | 90.19 | 46.09 | 99.459 |
| R27/gpu/prefill | 28.93 | 180.25 | 95.023 |
| R27/npu0/decode | 92.69 | 48.25 | 100.000 |
| R27/npu1/decode | 92.71 | 46.44 | 99.508 |

짧은 상태는 전체 수집 PASS여도 coverage가 낮다. S5t prefill의 사례를 원값으로 남긴다.
R27 gpu/prefill/utilization: 평균 28.926, coverage 95.022856%, estimated.
R27 system/prefill/cpu: 평균 8.540, coverage 4.548659%, estimated.
R28 gpu/prefill/utilization: 평균 1.990, coverage 90.560655%, estimated.
R28 system/prefill/cpu: 평균 8.529, coverage 0.016171%, estimated.
R29 gpu/prefill/utilization: 평균 0.000, coverage 50.286873%, estimated.
R29 system/prefill/cpu: 평균 미수집, coverage 0.000000%, not_collected.
부하가 없었다는 의미로 미수집을0으로 치환하지 않는다. GDDR7·GDDR6·시스템 RAM은 서로 다른 공간이다.

![자원 시계열·단계 coverage](figures/05_resources.png)

그림5. 출처: sweep3/dataset/resource_timeseries.csv, results.csv phase_resources. 시계열 measured, 귀속 estimated.

## 6. 데이터 전송 효율과 병목

T01=Δbytes/Δxfer_seconds/10^9이며 NIXL 계측 경과시간 기준이다. T04=63.008GB/s는 링크 규격 이론치다.
T03·NPU T05는 copy_ 동기 여부 미확인(H4), T02는 전송 count 단위 미확인(H5)으로 미수집이다.
M08은 xfer start~done, M09a는 host copy 호출 합의 요청평균이며 겹칠 수 있어 임계 경로로 단순 합산하지 않는다.

| S5t/decoder | T01 GB/s | M08 s | M09a s | M09b s | T06 GB/s(하한 추정) | T07 %(하한 추정) |
|---|---:|---:|---:|---:|---:|---:|
| R27 i4096_o256/decode0 | 0.388 | 0.388880 | 0.317965 | 0.000000 | 58.022 | 22.665 |
| R27 i4096_o256/decode1 | 0.386 | 0.391211 | 0.282179 | 0.000000 | 58.645 | 22.908 |
| R28 i2176_o2176/decode0 | 0.398 | 0.201676 | 0.190184 | 0.000000 | 66.368 | 25.925 |
| R28 i2176_o2176/decode1 | 0.377 | 0.212952 | 0.173539 | 0.000000 | 66.383 | 25.931 |
| R29 i256_o4096/decode0 | 0.170 | 0.055700 | 0.054703 | 0.000000 | 80.411 | 31.410 |
| R29 i256_o4096/decode1 | 0.172 | 0.055019 | 0.052618 | 0.000000 | 80.397 | 31.405 |

S2 decoder T01은 0.403018/0.385211GB/s다(R04).
9월 profiling.csv의 대응값0.377865/0.366343GB/s는 선택 로그 구간이고 이번은 경계 차분이므로 규모만 비교한다.
UCX backend·host-bounce는 H0/S2 로그로 확인했지만 실제 transport/lane은 미확인(H5)이다.
낮은 T01/이론치 비율만으로 PCIe 포화를 주장하지 않는다.
NPU T06/T07은 가중치·문맥 기반 추정 bytes를 호스트 decode span 합으로 나눈 하한 추정이며,
메모리 컨트롤러 실측 효율이 아니다. 이론 분모는 NPU_MEM_BW_GBPS=256GB/s다.
GPU T06/T07은 WP9 접근 바이트 모델 미확인으로 미수집, R09b도 device 시간 누락으로 미수집이다.
**copy_ 동기 여부 미확인(H4)이므로 h2d_ns는 호스트 호출 시간 기준이며, H2D 전송 대역폭으로 단정하지 않는다.**

![전송 처리율과 이론 링크](figures/06_transfer.png)

그림6. 출처: sweep3/results.csv transfer, S2·S5t. T01 measured; 규격 대비 비율은 참고치.

### S7: 측정 PASS, 출력 정합성 FAIL(결함 보고)

sweep3의 reorder0/1 처리량은 62.216/62.260token/s지만,
**reorder1의 성능을 최적화 효과로 해석하지 않는다.** 두 출력은16/16요청 불일치다(R34·R35).
기존 S7 조사에서 첫 토큰8개·두 번째8개부터 갈라지고 비문·숫자 반복이 관측됐다.
추가 s7check_reorder1_monitor는 엔진 계측 OFF에서도 trace reorder1과16/16 일치, reorder0과0/16 일치했다.
원본/계측 복사 함수의 view·permute·unsqueeze·contiguous·copy_와 인덱스·dtype·shape 검사도 동일했다.
따라서 이번 출력 결함의 원인으로 계측 영향을 배제하고 공통 reorder 경로의 정확성 결함으로 판단한다.
정확한 배치 전제·원소 대응 오류 위치는 추가 진단 사항이다. 근거: .notes/S7_reorder_output_2026-11-11.md 및 해당 requests.jsonl.
M09b는 decoder0/1 평균 0.029954/0.027546초(R35.transfer)이며,
**“출력 정합성이 확보되지 않은 경로에서의 호스트 재배열 비용 참고치”**로만 남긴다.

## 7. 에너지 효율과 유휴 전력

R11=가속기 에너지/출력토큰, R12=역수. 본측정 전력을 사다리꼴 적분한 추정이며 유휴 전력을 빼지 않았다.
CPU·호스트 RAM·팬·전원 손실은 포함하지 않는다. 전체 energy coverage는
95.38~99.95%다.
출처각R.energy 및 dataset/energy.csv.

| 조건/i/o | 에너지 B0→PDD kJ | R11 J/token | R12 token/J | R11 변화% | 출처 |
|---|---|---|---|---:|---|
| s1/i512_o128 | 11.410 → 26.283 | 0.506 → 1.167 | 1.974 → 0.857 | 130.35 | R01,R02 |
| s2/i4096_o256 | 7.648 → 11.887 | 1.867 → 2.902 | 0.536 → 0.345 | 55.42 | R03,R04 |
| s3a_b1/i2048_o256 | 20.900 → 36.074 | 2.551 → 4.404 | 0.392 → 0.227 | 72.60 | R05,R06 |
| s3a_b4/i2048_o256 | 7.776 → 16.741 | 0.949 → 2.044 | 1.053 → 0.489 | 115.29 | R07,R08 |
| s3a_b2/i2048_o256 | 11.780 → 23.346 | 1.438 → 2.850 | 0.695 → 0.351 | 98.17 | R09,R10 |
| s3b_c2/i2048_o256 | 21.822 → 39.724 | 2.664 → 4.849 | 0.375 → 0.206 | 82.04 | R11,R12 |
| s3b_c4/i2048_o256 | 11.843 → 24.482 | 1.446 → 2.989 | 0.692 → 0.335 | 106.72 | R13,R14 |
| s3b_c8/i2048_o256 | 8.354 → 16.536 | 1.020 → 2.019 | 0.981 → 0.495 | 97.94 | R15,R16 |
| s4_qwen3-0.6b/i2048_o256 | 28.219 → 106.623 | 0.363 → 1.370 | 2.758 → 0.730 | 277.84 | R17,R18 |
| s4_qwen3-4b/i2048_o256 | 85.766 → 213.349 | 1.102 → 2.741 | 0.907 → 0.365 | 148.76 | R19,R20 |
| s5/i4096_o256 | 7.651 → 11.776 | 1.868 → 2.875 | 0.535 → 0.348 | 53.93 | R21,R24 |
| s5/i2176_o2176 | 37.016 → 54.165 | 1.063 → 1.556 | 0.941 → 0.643 | 46.33 | R22,R25 |
| s5/i256_o4096 | 58.833 → 81.276 | 0.898 → 1.240 | 1.114 → 0.806 | 38.15 | R23,R26 |
| s6/i4096_o1 | 33.350 → 45.068 | 119.109 → 160.956 | 0.008 → 0.006 | 35.13 | R30,R32 |
| s6/i32_o4096 | 57.517 → 77.253 | 0.878 → 1.179 | 1.139 → 0.848 | 34.31 | R31,R33 |

전체 평균 전력 감소가 완료시간 증가를 상쇄하지 못할 수 있다. 출력1토큰 S6의 높은 J/token은 작은 분모 효과도 포함한다.
idle 기준선을 따로 빼지 않아 순수 동적 추론 에너지나 장치 중단 시 절감량은 계산하지 않는다.

![에너지 효율과 idle 전력](figures/07_energy.png)

그림7. 출처: sweep3/results.csv energy·phase_resources 및 dataset/resource_timeseries.csv. estimated.

## 8. 하드웨어별 연산 특성

Qwen2.5-3B-Instruct의 단일 장치 vLLM LLM API 오프라인 프로파일이다. warm-up 뒤 측정 generate를 수행했다.
GPU·NPU prefill은 i4096/o1 × 4, GPU decode는 i32/o256 × 4다.
NPU decode는 i32/o256 및 i32/o64 × 4 모두 trace 무결성 문제로 미수집이다.
출처: `h6b/<장치·phase>/meta.json`, `.notes/H6b_2026-11-10.md`.

### 유형 분류와 비율

이름별 상위20을 다시 묶지 않고 **원자료 전체 slice**를 유형으로 분류한 뒤 카테고리별 inclusive 시간 합으로 나눴다.
GPU는 GEMM/WMMA/GEMV→matmul, flash/attention→attention, norm, elementwise/활성화, 기타 순으로 분류한다.
NPU는 이름의 숫자를 지우고 DMA 카테고리, linear/matmul/GEMM, attention/attn, norm, elementwise/활성화로 분류한다.
규칙에 맞지 않으면 기타다. 정확한 정규식과 우선순위는 `profiler/operator_stats.py`의 TYPE_RULES에 있다.
시간은 measured이며 **유형은 이름 규칙에 의한 분류**다. 0%는 해당 이름 규칙에 잡힌 시간이 없다는 뜻이지 해당 연산이 실행되지 않았다는 뜻이 아니다.

| 장치·phase / 카테고리 | matmul | linear | attention | norm | elementwise | DMA | 기타 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| gpu / prefill / kernel | 70.7860 | 0.0000 | 22.7315 | 2.0736 | 1.2728 | 0.0000 | 3.1360 |
| gpu / decode / kernel | 81.4450 | 0.0000 | 9.7851 | 2.1900 | 3.1228 | 0.0000 | 3.4571 |
| npu / prefill / Neural Engine Clusters | 0.0000 | 59.9977 | 0.0000 | 0.0000 | 0.7350 | 0.0000 | 39.2672 |
| npu / prefill / Neural DMA | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 100.0000 | 0.0000 |
| NPU decode(256·64토큰) | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 | 미수집 |

모든 값은 %. 출처: `h6b/{gpu_prefill,gpu_decode,npu_prefill}/operators_by_type.csv`;
통합본은 `sweep3/dataset/operators_by_type.csv`. NEC와 DMA는 별도 분모이며 시간을 더하지 않는다.
GPU prefill은 matmul 70.7860%, attention 22.7315%이고 decode는 각각 81.4450%, 9.7851%다.
이 이름 분류에서는 decode의 matmul 비중이 더 크다. GPU decode 전체 generate에는 초기 prefill도 포함한다.
NPU prefill NEC의 linear는 59.9977%지만 기타가 39.2672%여서 유형 해석에 상당한 공백이 있다.
NPU 내부 command와 GPU fused kernel의 분할·명명 단위 및 관측 범위가 달라 위 비율로 장치 우열을 판단하지 않는다.
특히 NPU에서 attention 0%를 attention 계산 부재로 해석하지 않는다(융합·하위 명령 가능성은 추정).

### 무결성과 집계 범위

GPU 두 파일은 gzip·Perfetto의 kernel/cpu_op 개수가 일치하고 버려진·미종료 slice가 0이다.
GPU decode 커널 시간의 99.827082%가 스텝에 연결되며 순수 decode 255스텝 커널 합은 1337.779144ms다.
NPU prefill 전체 `rbln_20261110_120819072.pb`는 660,932,611bytes이며 전체/실행별 PB 합계는 1,316,636,786bytes다.
전체 파일 재검사에서도 버린 slice 17,032개, NEC·Neural DMA 미종료 각각 511개가 나와 전체 집계를 사용하지 않았다.
**깨끗한 마지막 본측정 `_257.pb` 한 파일만** 사용했다: 3,808,148bytes, 버린·미종료·원본 종료<시작 모두 0.
NEC 8,576개(56.239480ms), Neural DMA 1,582개(28.136035ms)의 마지막 chunked-prefill 모듈이며 4요청 전체의 대표값이 아니다.
출처: 해당 PB, `h6b/npu_prefill/diagnostics.json`, 같은 H6b 메모의 전체/마지막 파일 대조.

| NPU decode 출력 길이 | 마지막 PB | 원본 종료<시작 | 버린 slice | NEC / Neural DMA 미종료 |
| --- | --- | ---: | ---: | --- |
| 256 | rbln_20261110_121548351_519.pb | 18,496 | 17,474 | 511 / 511 |
| 64 | rbln_20261110_142246607_135.pb | 18,054 | 17,032 | 511 / 511 |

두 길이 모두 `not_collected`, reason="RBLN Profiler trace 무결성 문제(종료<시작 이벤트)"다.
64토큰 전체 PB에서도 종료<시작 2,292,890개, 버린 slice 2,163,064개를 확인했다.
원인은 **추정: RBLN Profiler 기록/타임스탬프 생성 문제**이며 내부 원인은 미확인(H6b)이다.
버린 slice를 제외한 연산자 비율은 만들지 않았다. NPU decode 분포와 GPU 대비 속도 비교는 보류한다.
출처: `h6b/npu_decode/operators.md`, `h6b/npu_decode_short/diagnostics.json`; H6b 메모.

![이름 기반 연산 유형 분포](figures/08_types.png)

그림 8. 출처: h6b/*/operators_by_type.csv. 시간 measured; 이름 규칙 분류. GPU 전체 generate / NPU prefill 마지막 모듈; NPU decode 미수집.


## 9. 모니터링 부하(PER-001·PT-002)

PER-001 1차·최종 모두4블록 PASS. S2 PDD none 서비스에서 OFF·ON·ON·OFF를 반복했다.
두 지표90% 양측t CI의 상한이5% 이하여야 합격이다. 아래 단위는%.

| 측정 | d_tp 평균[90%CI] | d_lat 평균[90%CI] | 근거 |
|---|---|---|---|
| per001_r3 | -0.049765 [-0.182904,0.083374] | -0.037643 [-0.105786,0.030500] | per001_r3/overhead/overhead.json |
| per001_final | 0.139838 [0.034939,0.244737] | 0.114780 [0.050106,0.179455] | per001_final/overhead/overhead.json |

최종 측정 커밋3a6ff3d 이후 측정 경로는 주석만 변경됐다(test_report.md). r1b 포트·r2 dirty 실패는 합격 표본에 넣지 않았다.

![PER-001 1차 블록 결과](figures/09_overhead.png)

그림9. 출처: per001_r3/overhead/overhead.json. measured; 그림은1차, 최종 판정 수치는 위 별도 표.

### PT-002 및 재기동 참고

| 실행 | 모드 | 출력 token/s | 평균 E2E(s) | monitor 대비 처리량 / E2E 변화(%) | 근거 |
| --- | --- | ---: | ---: | --- | --- |
| s2_pdd | monitor | 62.441 | 48.757 | 기준 | s2_pdd/s2/profile/summary.json |
| s8_r1 | trace | 62.380 | 48.824 | -0.097 / +0.137 | s8_r1/s2/profile/summary.json |
| s8_r2 | trace | 62.529 | 48.627 | +0.142 / -0.268 | s8_r2/s2/profile/summary.json |

이는 시점·기동 상태가 다른 참고 비교이며 PER-001처럼 교차 블록·신뢰구간을 갖춘 trace 부하 판정은 아니다.
s8_r1→r2 서비스 기동은 304.997→153.212초이고 출력 토큰은 16/16 요청이 같았다.
캐시 재사용 효과로 해석할 단서는 있으나 모든 서비스 조건의 재사용 안전성을 확정하지 않는다(미확인 H7 일부).
출처: 각 run.json `service_start`, requests.jsonl; `.notes/HW_H4_H6_H7_2026-11-09.md`.


## 10. 한계와 미확인 사항

| 항목 | 제한·후속 조치 |
|---|---|
| 목표 시간·단일 측정 | 28/28 측정PASS이나 요청 상향 미적용으로5개 workload 시간 미달. 상향 적용·재실행 또는 예외 승인 필요 |
| 출력 정합성 | S7 reorder1 FAIL(결함 보고), 일반 cross-device correctness는 not_evaluated. 측정PASS와 구분 |
| H4 | copy_ 동기성·device 의미 미확인. T03/R09b 미수집, NPU T06/T07 하한 추정 |
| H5·H3 | 전송 count 단위·실제UCX lane·링크 부하 중 성능 미확인 |
| H2 | 짧은 상태 coverage와 센서 해상도 제한; 전체 수집PASS가 모든 단계 평균의 신뢰성을 보장하지 않음 |
| H6·H6b | 온라인 MP 제약, 오프라인 NPU prefill 부분 집계·decode trace 무결성 문제 |
| H7 | 캐시 재사용은 일부 조건 관측, 모델/SDK 변경 전반 안전성 미검증 |
| M12 | other_seconds 미구현(후속); M14a의 잔여 구성비와 별개 |

H0의 요청 매칭은 성공했으나 짧은 창의 표본 부족으로 전체 analysis_status=INCOMPLETE다.
이를 sweep3 PASS와 같은 근거 수준으로 사용하지 않는다.

### 개발팀·제조사에 보고한 사항

아래는 사용자 전달에 따른 보고 사항 정리다. 발송일·접수번호·벤더 회신은 제공되지 않아 확인하지 않았다.
이번 작업에서 메시지를 발송하거나 해결됐다고 판정하지 않았다. 상세 전달 문안은 .notes/team_share_2026-11-11.md.

| 사항 | 증상·근거 | 요청 사항 |
|---|---|---|
| B0 배치8 샘플러 | 전체 NPU 추론에서 num_compute_units 미구현, PDD decode8은 성공; sweep1 로그 | RBLN 플랫폼의 Triton sampler 지원·우회 계약 검토 |
| RBLN Profiler decode | 256/64토큰 PB의 종료<시작·discarded/unfinished slice; H6b 메모 | timestamp·trace export 원인 및 수정 SDK 확인 |
| reorder1 출력 | OFF/ON 모두 같은 비정상 출력, r0와 불일치; S7 메모 | KV source/destination 의미·축·첫 step logits 대조 및 정합성 수정 |
| 실행 환경 취약 패키지 | QA CUDA171건/RBLN104건, 벤더 skip 있음; security_check.md | 팀 소유 venv의 호환성 있는 수정판 검토·외부 입력/접근 제한 |

도구 Pillow12.3.0 잔여39건도 알려진 제한이다. Python3.10 환경의13.x 설치 제약과
외부 이미지 해석 없는 PNG 출력 사용을 구분해 기록했다. 로컬 바인드는 취약점 수정의 대체가 아니다.

## 11. SFR-001 담당 팀 참고 사항

우선순위는 reorder 출력 정확성 복구, 플랫폼/Profiler 결함 해결, 안전한 실행 환경 관리다.
성능 과제는 decode 역할 배치·host-bounce 경로·배치와 큐 지연의 공동 튜닝이다.
S5t의 decode 비중과 처리량 표는 조사 우선순위 근거이지 단일 병목의 인과 확정이 아니다.
reorder1을 빠르거나 유효한 최적화라고 권고하지 않으며 M09b도 비정합 경로의 호스트 비용 참고치다.
목표 시간을 충족한 반복 측정·정합성 검증 뒤 최적화 효과를 확정한다.

## 부록: 숫자 출처 색인

모든 아래 경로는 sweep3 기준이며 표의 R은 해당 summary의 client/transfer/memory_bandwidth/phase_resources/energy를 뜻한다.

| ID | 시나리오/workload | summary 경로 |
|---|---|---|
| R01 | s1_b0/i512_o128 | `runs/s1_b0_2/i512_o128/profile/summary.json` |
| R02 | s1_pdd/i512_o128 | `runs/s1_pdd_2/i512_o128/profile/summary.json` |
| R03 | s2_b0/i4096_o256 | `runs/s2_b0_2/i4096_o256/profile/summary.json` |
| R04 | s2_pdd/i4096_o256 | `runs/s2_pdd_2/i4096_o256/profile/summary.json` |
| R05 | s3a_b1_b0/i2048_o256 | `runs/s3a_b1_b0_2/i2048_o256/profile/summary.json` |
| R06 | s3a_b1_pdd/i2048_o256 | `runs/s3a_b1_pdd_2/i2048_o256/profile/summary.json` |
| R07 | s3a_b4_b0/i2048_o256 | `runs/s3a_b4_b0_2/i2048_o256/profile/summary.json` |
| R08 | s3a_b4_pdd/i2048_o256 | `runs/s3a_b4_pdd_2/i2048_o256/profile/summary.json` |
| R09 | s3a_b2_b0/i2048_o256 | `runs/s3a_b2_b0_1/i2048_o256/profile/summary.json` |
| R10 | s3a_b2_pdd/i2048_o256 | `runs/s3a_b2_pdd_1/i2048_o256/profile/summary.json` |
| R11 | s3b_c2_b0/i2048_o256 | `runs/s3b_c2_b0_2/i2048_o256/profile/summary.json` |
| R12 | s3b_c2_pdd/i2048_o256 | `runs/s3b_c2_pdd_2/i2048_o256/profile/summary.json` |
| R13 | s3b_c4_b0/i2048_o256 | `runs/s3b_c4_b0_2/i2048_o256/profile/summary.json` |
| R14 | s3b_c4_pdd/i2048_o256 | `runs/s3b_c4_pdd_2/i2048_o256/profile/summary.json` |
| R15 | s3b_c8_b0/i2048_o256 | `runs/s3b_c8_b0_2/i2048_o256/profile/summary.json` |
| R16 | s3b_c8_pdd/i2048_o256 | `runs/s3b_c8_pdd_2/i2048_o256/profile/summary.json` |
| R17 | s4_qwen3-0.6b_b0/i2048_o256 | `runs/s4_qwen3-0.6b_b0_2/i2048_o256/profile/summary.json` |
| R18 | s4_qwen3-0.6b_pdd/i2048_o256 | `runs/s4_qwen3-0.6b_pdd_2/i2048_o256/profile/summary.json` |
| R19 | s4_qwen3-4b_b0/i2048_o256 | `runs/s4_qwen3-4b_b0_2/i2048_o256/profile/summary.json` |
| R20 | s4_qwen3-4b_pdd/i2048_o256 | `runs/s4_qwen3-4b_pdd_2/i2048_o256/profile/summary.json` |
| R21 | s5_b0/i4096_o256 | `runs/s5_b0_2/i4096_o256/profile/summary.json` |
| R22 | s5_b0/i2176_o2176 | `runs/s5_b0_2/i2176_o2176/profile/summary.json` |
| R23 | s5_b0/i256_o4096 | `runs/s5_b0_2/i256_o4096/profile/summary.json` |
| R24 | s5_pdd/i4096_o256 | `runs/s5_pdd_2/i4096_o256/profile/summary.json` |
| R25 | s5_pdd/i2176_o2176 | `runs/s5_pdd_2/i2176_o2176/profile/summary.json` |
| R26 | s5_pdd/i256_o4096 | `runs/s5_pdd_2/i256_o4096/profile/summary.json` |
| R27 | s5t_pdd/i4096_o256 | `runs/s5t_pdd_2/i4096_o256/profile/summary.json` |
| R28 | s5t_pdd/i2176_o2176 | `runs/s5t_pdd_2/i2176_o2176/profile/summary.json` |
| R29 | s5t_pdd/i256_o4096 | `runs/s5t_pdd_2/i256_o4096/profile/summary.json` |
| R30 | s6_b0/i4096_o1 | `runs/s6_b0_2/i4096_o1/profile/summary.json` |
| R31 | s6_b0/i32_o4096 | `runs/s6_b0_2/i32_o4096/profile/summary.json` |
| R32 | s6_pdd/i4096_o1 | `runs/s6_pdd_2/i4096_o1/profile/summary.json` |
| R33 | s6_pdd/i32_o4096 | `runs/s6_pdd_2/i32_o4096/profile/summary.json` |
| R34 | s7_pdd_r0/i4096_o256 | `runs/s7_pdd_r0_2/i4096_o256/profile/summary.json` |
| R35 | s7_pdd_r1/i4096_o256 | `runs/s7_pdd_r1_2/i4096_o256/profile/summary.json` |
| R36 | s8_pdd/i4096_o256 | `runs/s8_pdd_2/i4096_o256/profile/summary.json` |

SEP1-B/P: tests/hetero/fixtures/real/{b0,p0}_qwen3_0p6b_b1_ctx1024/workload_i512_o128_b18/summary.json.
SEP2-B/P: <9월 패키지>/runs/{b0,p0}_qwen2p5_3b_bf16_b4_ctx4352/A_i4096_o256_b16/summary.json.
기타 근거: .notes/H0_2026-11-06.md, S1_S2_repro_2026-11-06.md, WP7b_2026-11-07.md,
M14a_KV_transport_2026-11-07.md, HW_H4_H6_H7_2026-11-09.md, H6_fix_2026-11-09.md,
H6b_2026-11-10.md, S7_reorder_output_2026-11-11.md(모두 .notes 기준).
로컬 메모는 커밋 산출물이 아니다. 전달용 근거는 외부 결과와 납품 데이터셋·시험 보고서에 보존한다.
