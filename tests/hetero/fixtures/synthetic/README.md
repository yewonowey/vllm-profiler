# 손으로 구성한 원자료와 기대값

각 세트는 `requests.jsonl`, 예정 개수를 담은 `config.json`, 역할과 주소를 담은
`service_config.json`, 손계산한 `expected.json`으로 구성된다. 모든 시각은 초이며
옛 loadgen 원자료 필드 이름을 쓴다. 요청별 계산 지표는 `expected.json`에만 둔다.
`success`는 옛 형식에 존재하는 판정 필드다. 주소는 문자열 대조용이며 접속하지 않는다.

| 세트 | 손계산 근거 |
| --- | --- |
| multi_token | arrival=100, assigned=101, send=102, token=104·106·108, completed=110. Queue=1, TTFT=4, E2E=10, service=8, TPOT=2, ITL=[2,2]. |
| one_token | arrival=100, assigned=100, send=101, token=103, completed=104. TTFT=3, E2E=4, service=3. TPOT은 `not_collected`, reason=`not_applicable`에 대응하는 null 기대값. |
| failed | arrival=100, send=101, completed=102, HTTP 500. E2E=2, service=1, 출력 토큰 없음, 성공 집합은 공집합. |
| b0_three_devices | multi_token과 같은 요청 3개를 GPU·NPU0·NPU1에 하나씩 배정. makespan=10, 처리량=3/10 요청/초, 9/10 출력 토큰/초. |
| pdd_skew | multi_token과 같은 요청 4개의 `x-decode-target`이 모두 decode0. prefill·decode0 기대 집합은 4개, decode1은 0개. 처리량=4/10 요청/초, 12/10 토큰/초. |
| missing_two | one_token과 같은 원자료 14개, 예정 16개. req0014·req0015 누락, 모두 성공이어도 run_status=FAILED. makespan=4, 관측 처리량=14/4 요청/초 및 토큰/초. |

`expected.json`의 `requests`는 요청별 기대 지표, `expected_ids_by_role`은 성공
요청의 서버별 기대 ID 집합이다. `planned_ids`는 원자료 개수로 예정 개수를
대체하는 오류를 잡기 위한 독립 목록이다. 구현된 분석기는 포함하지 않는다.
