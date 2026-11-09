# WP5 실행기와 원자료 수집

CUDA Python에서 `python -m tools.hetero.profiler.run` 또는
`python tools/hetero/profiler/run.py`로 실행한다. 핵심 모듈은 표준 라이브러리만
사용하며 loadgen의 토크나이저는 기존 실행 환경을 사용한다.

```bash
"$CUDA_PY" -m tools.hetero.profiler.run \
  --configuration pdd --mode trace --run-dir "$RUN_DIR" \
  --workloads workloads.json --model-path "$MODEL_PATH" --model-name qwen \
  --cuda-python "$CUDA_PY" --rbln-python "$RBLN_PY"
```

`RUN_DIR`는 저장소 밖의 새 디렉터리 또는 빈 디렉터리다. 나머지 서비스 인자는
orchestrate start에 전달한다. orchestrate의 run 디렉터리는 자동으로
`<service_run>/service/`로 지정한다. 실행기는 이 하위 폴더를 미리 만들지 않는다.
명시적인 `--cache-dir` 역시 저장소 밖이어야 하며, 생략하면 `service/cache/`다.

## Workloads JSON

최상위는 비어 있지 않은 배열이다. 아래 필드는 모두 필수이며 알 수 없는 필드는
거부한다. 이름은 영숫자로 시작하고 영숫자·밑줄·점·하이픈만 허용한다.
이름 중복, `service`, `monitor` 등 실행기 산출물과 충돌하는 이름은 거부한다.
토큰 수·요청 수·PDD 동시성은 양의 정수, seed·warmup은 음이 아닌 정수다.
불리언은 정수로 받지 않는다. `warmup`은 엔드포인트별 반복 횟수다.

B0 (`--configuration baseline`):

```json
[
  {
    "name": "short",
    "input_tokens": 512,
    "output_tokens": 128,
    "requests": 16,
    "seed": 7,
    "warmup": 1,
    "slots": {"gpu": 2, "npu0": 1, "npu1": 1}
  }
]
```

slots에는 세 역할이 모두 있어야 한다. 값은 음이 아닌 정수이고 합은 양수여야 한다.
0인 역할에는 loadgen worker를 배정하지 않는다. 서버는 orchestrate의 기존 구성대로
모두 시작하고, 수집도 모든 서버를 대상으로 한다.

PDD (`--configuration pdd`):

```json
[
  {
    "name": "short",
    "input_tokens": 512,
    "output_tokens": 128,
    "requests": 16,
    "seed": 7,
    "warmup": 1,
    "concurrency": 4
  }
]
```

PDD 요청은 proxy로 보낸다. decoder 배정은 응답의 `x-decode-target`을 사용한다.
기대 ID를 요청 번호나 round-robin 순서로 추정하지 않는다.

## 실행 순서와 디렉터리 구조

다음은 trace/deep에서 파일이 생성되는 단계 순서다. 프로세스가 병렬로 쓰는
단계 내부 파일의 세부 생성 시각은 달라질 수 있다.

1. `<service_run>/monitor/`를 만든 뒤 단계 종료마다 `run.json`을 저장한다.
   실행 인자·workloads·모드와 `steps` 목록을 기록한다. 각 단계는
   `{name, start, end, ok, error}`이며 start/end는 MONOTONIC 나노초다.
   로그의 run ID는 이 디렉터리 이름이다.
2. Collector: `otel/`, `monitor/otelcol.log`, `otel/traces.jsonl`.
   traces 파일의 최초 기록 시각은 Collector의 배치 수출 시점에 따른다.
3. 서비스 시작: `monitor/service_start.log`. orchestrate가 직접 `service/`를 만들고
   `logs/`, `cache/`, `processes.json`, `config.json`, `commands.sh`를 그 아래에 쓴다.
   엔진이 trace 이상에서 `rbln_metrics/<NPU 역할>/events_*.jsonl`을 쓴다.
   deep의 `torch_traces/<역할>/`은 각 profiler가 생성한다.
4. PDD trace/deep: 두 decoder의 `kv_layout.use_host_buffer=true`를 최대 30초 확인한다.
   확인 실패 시 warm-up과 본측정을 시작하지 않고 정리한다.
5. all-smi: `monitor/all-smi.log`. `PDD_ALLSMI_PORT`(기본 19090)의 사용 여부를
   먼저 검사하고 `/-/ready`를 최대 60초 기다린다. 이어 `links.json`을 기록한다.
   links 수집 실패는 단계 오류와 로그로 남기고 측정을 계속한다.
6. workload별:
   - `monitor/<이름>-warmup.log`, `<이름>/warmup/warmup_requests.jsonl`.
     기존 loadgen의 warmup-only 산출물을 그대로 사용한다. 이 호출은
     `requests.jsonl`이나 `loadgen_run.json`을 생성하지 않는다.
   - `monitor/scrape.log`, `<이름>/monitor/metrics.jsonl`,
     `<이름>/monitor/boundaries.jsonl`의 before 행.
   - deep: `<이름>/profile_control.jsonl`에 서버별 start_profile 전송 시각·결과.
   - `monitor/<이름>-measure.log`, `<이름>/warmup_requests.jsonl`(빈 파일),
     `<이름>/requests.jsonl`, `<이름>/config.json`, `<이름>/loadgen_run.json`.
   - deep: stop_profile 전송 기록. 이후 after 경계 행을 추가하고 scrape를 정지한다.
7. `trace_wait.json`: 모든 workload의 성공 요청에 해당하는 span을 최대 30초 기다린다.
   `complete`와 빠진 `role`·서버 `request_id` 목록을 쓴다. 시간 초과는
   `analysis_status=INCOMPLETE`와 종료 코드 1로 알린다.
8. all-smi 정지 → `monitor/service_stop.log`,
   `service/rbln_smi_after_stop.json` → Collector 정지. 예외가 발생해도 이 순서로
   시작된 프로세스를 정리한다. 단계별 정리 실패도 기록하고 다음 정리를 계속한다.
9. workload마다 `analysis.py --run-dir <service_run>/<workload>`를 호출한다.
   현재는 파일이 없어 `analysis pending (WP7a)`를 출력한다. WP7a는 workload의
   부모에서 공용 trace와 `service/config.json`을 읽는 이 호출 규약을 이어받는다.

none은 서비스·warm-up·본측정·분석 호출만 수행한다. monitor는 Collector, 엔진 이벤트,
torch profiler와 span 대기를 생략한다. trace 이상은 proxy를 제외한 모든 서버에
OTLP 인자와 OTEL 환경을 넣는다. deep은 torch profiler JSON을 단일 argv 원소로 넣고
NPU에 `RBLN_PROFILER=1`을 추가한다. 생성하는 환경 값이 같은 이름의 사용자 지정값보다
우선하며, 생성 profiler 인자와 중복되는 사용자 role 인자는 오류로 처리한다.

## 원자료와 요청 ID

`expected_ids(rows, config)`는 **클라이언트 ID**의 역할별 집합을 반환한다.
성공 기준은 기존 loadgen의 `request_succeeded`와 공유한다: HTTP 2xx, error가 None,
실제 출력 토큰 수와 요청 출력 토큰 수 일치. 입력 토큰 수 및 예정 ID 집합 검증은 WP7a다.
사용되지 않은 decoder도 빈 집합으로 남긴다. 잘못된 target은 오류로 처리한다.
`service_config(run_dir)`는 `run_dir/service/config.json`을 읽는다.

`server_request_id(client_id)`는 단일 prompt·n=1인 현재 loadgen에 대해
`cmpl-<client_id>-0`을 반환한다. 근거는 pip로 받은 vLLM 0.22.0 배포 소스다.

- [engine/serving.py:399](https://github.com/vllm-project/vllm/blob/v0.22.0/vllm/entrypoints/openai/engine/serving.py#L399): X-Request-Id 우선 사용.
- [completion/serving.py:144](https://github.com/vllm-project/vllm/blob/v0.22.0/vllm/entrypoints/openai/completion/serving.py#L144), 180: cmpl- 접두사와 prompt 인덱스 접미사.
- [output_processor.py:749](https://github.com/vllm-project/vllm/blob/v0.22.0/vllm/v1/engine/output_processor.py#L749): span은 external_req_id를 사용.

**TODO(verify: H0)**: CUDA·RBLN 실제 span의 `service.name`과 `gen_ai.request.id`를 확인한다.
Collector JSONL의 `resourceSpans/resource/attributes`, `scopeSpans/spans/attributes`
에서 두 값을 정확히 대조한다. 종료 중인 마지막 불완전 행은 다음 읽기까지 기다린다.
warm-up 등 추가 span은 기다림 조건에 넣지 않는다. 정확한 전체 집합 판정은 WP7a 몫이다.

준비 상태, host buffer, span 대기는 `scrape.wait_until(조건, 제한시간, 이름)`을
공유한다. 프로세스 시작·정지와 종료 코드는 `Monitors`에서 관리한다.
단계별 status/result와 별도의 cleanup_errors 목록은 단계의 ok/error로 합쳤다.

scrape는 endpoint별 HTTP 요청을 병렬로 수행하고, 응답을 JSONL로 보존한다.
`mono_ns`, `real_ns`는 전송 직전의 시각, `endpoint`는 지정한 이름,
`status`는 HTTP 상태 코드(연결/수신 실패는 0), `text`는 응답 원문 또는 오류 설명이다.
타임아웃은 0.8초이며 기본 주기는 1초다. boundary는 서버별로 동기 수집하고
`label=before|after`를 추가한다. SIGTERM은 현재 수집·줄 쓰기를 완료한 뒤 종료한다.

**남은 HW 확인:** H0의 실제 요청/trace·두 decoder kv_layout 연결,
H1의 실서비스 기동·정지, H2의 all-smi 수집, H3의 links 정보,
H6의 deep 프로파일 생성 및 정지 경계.
mock 자체의 세부 동작 시험은 **생략(HW 확인으로 대체)**한다.

## WP11 스윕과 결과표

CUDA Python으로 실행하고 `CUDA_PY`, `RBLN_PY`를 환경변수로 전달한다.
시나리오의 `service_args`는 서비스 옵션 이름과 값의 객체이며, 실제 모델 경로는
반복 가능한 `--model KEY=PATH`로만 전달한다. 출력과 공유 캐시는 저장소 밖에 둔다.

```bash
"$CUDA_PY" -m tools.hetero.profiler.sweep \
  --scenarios tools/hetero/scenarios/initial.json --sweep-dir "$SWEEP_DIR" \
  --model "qwen3-0.6b=$QWEN06_PATH" --model "qwen3-4b=$QWEN4_PATH" \
  --model "qwen25-3b=$QWEN25_PATH"
```

`--only NAME`을 반복하면 선택한 시나리오만 실행한다. 쌍 검사는 전체 선언에 적용한다.
`--cache-root`를 주면 서비스 조건별 해시 디렉터리를 사용하며 deep 캐시는 분리한다.
**TODO(verify: H7)**: 공유 캐시의 컴파일 호환성은 HW 확인이 필요하다.
성공한 시나리오는 재개 시 건너뛰고, 실패한 실행은 `_1`, `_2` 접미사로 보존한다.
선언을 바꾸면 새 sweep 디렉터리를 사용한다. `scenarios.json`에 시도·종료 코드를 기록하고,
`inputs/`에 workload 입력과 실행 로그를 보관한다. 시도별 표는 실패·미실행 행도 포함한다.

종료 시 `finalize_results.py --sweep-dir "$SWEEP_DIR"`를 호출한다.
`results.csv`의 클라이언트 지표는 수치 칸과 `client_metrics`의 정확도 메타데이터를 함께 제공한다.
서버·전송·자원·에너지 칸과 dataset의 중첩 셀은 JSON이다. 단위·출처·미수집 사유를 보존한다.
정합성은 workload 또는 profile의 `correctness.json`이 있을 때만 읽는다.
실패한 쌍은 비교 계산에서 제외하고, S7의 출력 비교는 완전한 저장 토큰 ID가 있어야 수행한다.

### S6 pilot과 요청 수 확정

`initial.json`의 시간은 S1·S2 실측 요청당 시간에 길이·배치·동시성 비율을 적용한 추정이다.
`estimation`에 근거·예상 시간·출력 토큰/s만 적용했을 때의 시간을 함께 남긴다.
Qwen3-4B는 미실측이므로 0.6B를 임시 기준으로 사용한다. 실제 시간과 컴파일 가능성은 확인해야 한다.
S6 prefill은 B0의 세 장치와 PDD GPU의 M07 역수로 처리 요청/s를 추정하고,
decode는 S2 출력 처리량을 사용한다. 요청 수에는 25% 여유를 적용하고 16의 배수로 올렸다.
S6의 512 상한 때문에 목표 시간을 보장할 수 없으므로 `pilot_adjust: true`를 유지한다.

1. S6 두 시나리오의 각 workload 요청 수를 16으로 바꾼 임시 시나리오 JSON을 저장소 밖에 만든다.
2. 새 pilot 디렉터리에서 아래처럼 S6만 실행한다. pilot 실행은 자동화하지 않는다.

   ```bash
   "$CUDA_PY" -m tools.hetero.profiler.sweep \
     --scenarios "$PILOT_JSON" --sweep-dir "$PILOT_DIR" \
     --model "qwen25-3b=$QWEN25_PATH" --only s6_b0 --only s6_pdd
   ```

3. 각 workload의 두 구성 모두 PASS인지 확인하고 summary의 makespan(s)으로
   `N = min(512, ceil(120 * 16 / min(B0 makespan, PDD makespan)))`을 계산한다.
   빠른 구성 기준이며 같은 pair/workload의 요청 수는 동일하게 적용한다.
   상한에 걸리면 예상 시간이 120초 미만일 수 있다는 점을 기록한다.
4. `initial.json`의 S6 요청 수와 추정 근거를 갱신하고 `pilot_adjust`를 false로 바꾼 뒤 커밋한다.
   본 스윕은 pilot과 다른 새 디렉터리에서 실행한다.
