# 보안 점검 결과

기준일: 2026-11-10. 이 문서는 개발한 성능 분석 도구의 정적 점검·의존성 검토 기록이다.
보안 인증이나 전체 실행 환경의 취약점 부재를 의미하지 않는다.
근거 자료의 위치는 결과 루트 기준 `qa_20261110/`로 표기한다.
원본 감사 대상은 `commit.txt`의 `7c7c4ef99e574b5660f7cd1a9c971f26e62be889`,
재검사는 `3a6ff3dcfce1621706d8913210175b344ab6bfdb`에 이번 수정이 적용된 작업 트리다.

## 1. 범위와 결론

| 대상 | 판정·조치 |
|---|---|
| 우리가 추가·변경한 코드 | B310 두 건, 판정 문자열 B105 한 건만 근거와 `nosec` 추가 |
| 옮겨 온 하네스·엔진·toy proxy 원본 줄 | 범위 밖(원본 코드). 출처·위험·권고만 기록; 변경 없음 |
| WP4 계측용 복사 함수 | 원본 assert를 복제한 10건은 우리 변경분으로 분류; 경고 유지 |
| 고정 도구 venv | 새 v2 번들·venv 설치. Pillow를 제외한 14개 배포 패키지 경고 0건 |
| Pillow 12.3.0 | 잔여 39건을 사용자 승인으로 기록. Python 3.11 이상 이전 시 13.x 갱신 권고 |
| CUDA·RBLN venv | 납품 범위 밖. 수정·업그레이드하지 않음 |
| 측정 코드 동작 | `run.py`, `scrape.py`, `overhead.py` AST가 수정 전과 동일. 로그 추가 없음 |

## 2. 개발보안 가이드 구현 단계 7분류

분류 근거: [행정안전부 소프트웨어 개발보안 가이드(2021)](https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000015&nttId=88956).
아래는 해당 분류에 대한 구현·잔여 위험 대응표이며 가이드의 모든 세부 항목을 진단했다는 뜻은 아니다.

| 분류 | 구현 근거 | 점검 결과·잔여 위험 |
|---|---|---|
| 입력 데이터 검증 및 표현 | `run.py` workload 검증, `orchestrate.py` role env/args 허용 목록, `sweep.py` 쌍 검사 | 기존 시험 통과. CLI URL·파일·실행 파일은 신뢰하는 운영자가 지정; 비신뢰 업로드용 인터페이스가 아님 |
| 보안 기능 | 서비스·proxy·Collector 루프백 설정, 번들 SHA256 검증 | 별도 인증·암호화 기능 없음. all-smi는 전체 인터페이스 바인드이므로 방화벽 필요; 적용 여부 미확인 |
| 시간 및 상태 | 요청 ID 대응, 원자료·계측 검증, `finally` 정리, 프로세스 종료 대기 | 측정 완전성 검사와 접근 통제는 별개. 원본 toy proxy 무제한 HTTP 대기는 유지 |
| 에러 처리 | 실패 원인·상태 보존, 계측 실패 경고, 분석 `not_collected` | B110은 원본 준비 대기 처리. 우리 코드에서 새로 조용히 삼키는 B110 없음 |
| 코드 오류 | 기존 단위시험, AST 비교, Bandit, `pip check` | 엔진 assert는 최적화 실행에서 제거됨. Python 최적화 옵션을 사용하지 말고 원본 개선은 팀 검토 |
| 캡슐화 | 원자료는 외부 결과 디렉터리, fixture 경로 치환, 공개 보고서와 원본 분리 | 파일 ACL·암호화·보존 기한은 자동 강제하지 않음. 토큰 ID와 장치 식별자도 공개 전 검토 필요 |
| API 오용 | subprocess argv 목록, 로컬 모델 tokenizer 옵션, HTTP timeout 사용 | B404/B603는 유지. 지정 바이너리·모델·URL의 신뢰가 전제이며 `nosec`는 검증 코드가 아님 |

## 3. Bandit 출처와 조치

`bandit_tools_hetero.json`, `bandit_engine_changed.json`의 각 항목을 원본과 대조했다.
하네스는 로컬 참고 원본의 같은 함수·문장을 비교했다. 엔진·toy proxy는
`git blame`과 `upstream/main`의 문장을 함께 확인했다. 이동 커밋만으로 원저작 여부를 판단하지 않았다.
표의 줄 번호는 최초 QA 기준이며 재검사에서 주석·기존 변경에 따라 이동할 수 있다.
특히 `operator_stats.py:65`는 현재 103행의 subprocess 호출에 해당한다.

| 검사 | 전 | 후 | 근거 |
|---|---:|---:|---|
| tools/hetero | 22 | 19 | `bandit_tools_hetero_after.json`, `.txt` |
| 엔진 변경 대상·toy proxy | 91 | 91 | `bandit_engine_changed_after.json`, `.txt` |
| 합계 | 113 | 110 | 전역 제외·심각도 필터 없이 해당 줄 세 건만 억제 |

Bandit는 남아 있는 경고 때문에 종료 코드 1이다. 0건 통과로 해석하지 않는다.
원본 88건, 우리 신규 14건, 하네스 변경 1건, 계측용 복제 10건으로 구분했다.

### 3.1 하네스·프로파일러: 모든 경고

경로 접두사는 `tools/hetero/`다. 위험도는 Bandit 값이다.
원본 행은 로컬 `harness_original`의 대응 파일 기준이다.

| 파일:QA행 | ID·위험도 | 출처·근거 | 판단·처리 |
|---|---|---|---|
| loadgen.py:27 | B615 MEDIUM | 우리 WP1 변경, `abc1cf04` | 로컬 tokenizer, `local_files_only=True`, `trust_remote_code=False`. 경고 유지; 모델 스냅샷·해시·쓰기 권한 관리 권고 |
| loadgen.py:103 | B105 LOW | 원본 94행 | 범위 밖(원본 코드). `return_token_ids`는 인증 비밀이 아닌 플래그; 오탐 판단 |
| loadgen.py:126 | B310 MEDIUM | 원본 118행 | 범위 밖(원본 코드). 임의 URL 스킴 위험; 운영 입력을 루프백 HTTP로 제한 권고 |
| orchestrate.py:17 | B404 LOW | 원본 16행 | 범위 밖(원본 코드). subprocess import 자체; 실행 인자 신뢰 관리 |
| orchestrate.py:78 | B603 LOW | 원본 35행 | 범위 밖(원본 코드). argv 실행; 바이너리·인자 변조 방지 권고 |
| orchestrate.py:173 | B310 MEDIUM | 원본 127행 | 범위 밖(원본 코드). 서비스 준비 URL; 외부 입력으로 URL을 대체하지 않을 것 |
| orchestrate.py:176 | B110 LOW | 원본 `wait_http_ready` 130행, `abc1cf04` | 범위 밖(원본 코드). 준비 중 예외 무시 후 재시도·전체 제한시간; 상세 원인 진단 약화. 후속 원본 검토 권고 |
| orchestrate.py:268 | B603 LOW | 원본 217행 | 범위 밖(원본 코드). 서버 argv 실행; 실행 환경 권한 관리 |
| profiler/monitors.py:5 | B404 LOW | 우리 코드, `e93e5f3d` | import, 유지 |
| profiler/monitors.py:63 | B603 LOW | 우리 코드, `e93e5f3d` | 고정 도구와 argv, 셸 미사용. 환경변수의 실행 파일 신뢰 필요; 유지 |
| profiler/operator_stats.py:11 | B404 LOW | 우리 코드, `d1b715ce` | import, 유지 |
| profiler/operator_stats.py:65 | B603 LOW | 우리 코드, `d1b715ce` | 지정 TP 바이너리·고정 SQL·trace 경로 argv. 비신뢰 trace 금지 권고; 유지 |
| profiler/overhead.py:181 | B105 LOW | 우리 코드, `a4e6920e` | PASS는 측정 판정, 비밀번호 아님. 근거 한 줄과 `nosec B105` |
| profiler/run.py:8 | B404 LOW | 우리 코드, `e93e5f3d` | import, 유지 |
| profiler/run.py:110 | B603 LOW | 우리 코드, `e93e5f3d` | 내부 하네스 argv 실행. 운영 입력 신뢰 전제; 유지 |
| profiler/run.py:121 | B310 MEDIUM | 우리 코드, `e93e5f3d` | runner가 서비스 설정에서 생성한 루프백 HTTP URL 사용. 근거 한 줄과 `nosec B310` |
| profiler/scrape.py:27 | B310 MEDIUM | 우리 코드, `e93e5f3d` | 정상 runner의 루프백 HTTP, 단독 CLI는 운영자 지정 URL. 그 신뢰 경계 명시 후 `nosec B310` |
| profiler/sweep.py:7 | B404 LOW | 우리 코드, `fa93bbbe` | import, 유지 |
| profiler/sweep.py:152 | B603 LOW | 우리 코드, `fa93bbbe` | 검증한 시나리오를 argv로 전달. 셸 미사용; 유지 |
| profiler/tools.py:7 | B404 LOW | 우리 코드, `f89885ef` | import, 유지 |
| profiler/tools.py:25 | B603 LOW | 우리 코드, `f89885ef` | 지정 실행 파일 버전 확인; 환경변수 변조 방지 권고, 유지 |
| profiler/tools.py:49 | B603 LOW | 우리 코드, `f89885ef` | 장치 질의 argv, 셸 미사용; PATH 신뢰 필요, 유지 |

`urlopen`은 스킴 제한을 자체 제공하지 않는다는 [Bandit B310 설명](https://bandit.readthedocs.io/en/1.7.10/blacklists/blacklist_calls.html#b310-urllib-urlopen)을 적용했다.
주석은 호출 맥락에 대한 판단이며, URL allowlist를 새로 구현하거나 원래 동작을 바꾸지 않았다.
루프백이어도 같은 호스트의 다른 사용자가 접근할 수 있으므로 인증과 동등하지 않다.

### 3.2 엔진·toy proxy: 모든 경고의 위치

아래 위치표의 판정 코드는 다음과 같다.

| 코드 | 위험도·처리·권고 |
|---|---|
| E | B101 LOW, 범위 밖(원본 코드). assert 제거 가능성; 최적화 옵션 사용 금지, 원본 검증 정책은 팀 검토 |
| C | B101 LOW, 우리 계측 복제본. 원본과 같은 10개 assert를 보존; 억제·변경 없음. E와 같은 위험·권고 |
| P | B113 MEDIUM, 범위 밖(원본 코드). 무제한 HTTP 대기로 자원 점유 가능; upstream timeout 정책 검토 권고 |

`runner`는 `vllm_rbln/v1/worker/rbln_model_runner.py`,
`worker`는 `vllm_rbln/distributed/kv_transfer/kv_connector/v1/rbln_nixl/worker.py`,
`proxy`는 `tests/torch_compile/e2e/v1/kv_connector/nixl_integration/toy_proxy_server.py`다.
upstream 행이 여러 개면 동일 문장 후보를 모두 기재했다. C의 근거는 원본 복사 함수의 동등한 assert다.

| 파일:QA행 | ID | 판정 | upstream/main 동일 문장 행 | blame |
|---|---|---|---|---|
| proxy:47 | B113 | P | 47, 66 | `c8f38802` |
| proxy:66 | B113 | P | 47, 66 | `c8f38802` |
| worker:142 | B101 | E | 139 | `fd0e9170` |
| worker:149 | B101 | E | 146 | `fd0e9170` |
| worker:264 | B101 | E | 196 | `fd0e9170` |
| worker:274 | B101 | E | 206 | `fd0e9170` |
| worker:308 | B101 | E | 240 | `fd0e9170` |
| worker:340 | B101 | E | 272 | `fd0e9170` |
| worker:346 | B101 | E | 278 | `fd0e9170` |
| worker:348 | B101 | E | 280 | `fd0e9170` |
| worker:408 | B101 | E | 340 | `fd0e9170` |
| worker:412 | B101 | E | 344 | `fd0e9170` |
| worker:435 | B101 | E | 367 | `fd0e9170` |
| worker:473 | B101 | E | 405 | `fd0e9170` |
| worker:521 | B101 | E | 453, 529 | `fd0e9170` |
| worker:522 | B101 | E | 454 | `fd0e9170` |
| worker:526 | B101 | E | 458 | `fd0e9170` |
| worker:597 | B101 | E | 453, 529 | `fd0e9170` |
| worker:620 | B101 | E | 552 | `fd0e9170` |
| worker:623 | B101 | E | 555 | `fd0e9170` |
| worker:646 | B101 | E | 578 | `fd0e9170` |
| worker:720 | B101 | E | 652 | `fd0e9170` |
| runner:174 | B101 | E | 172 | `877dd64f` |
| runner:435 | B101 | E | 433 | `b7f9d0a3` |
| runner:575 | B101 | E | 573 | `877dd64f` |
| runner:577 | B101 | E | 575 | `877dd64f` |
| runner:624 | B101 | E | 622 | `b7f9d0a3` |
| runner:657 | B101 | E | 655 | `6b187159` |
| runner:658 | B101 | E | 656 | `b33a4b6e` |
| runner:755 | B101 | E | 753 | `ef4633d9` |
| runner:756 | B101 | E | 754 | `ef4633d9` |
| runner:769 | B101 | E | 767 | `ef4633d9` |
| runner:943 | B101 | E | 941 | `b7f9d0a3` |
| runner:1032 | B101 | E | 1030 | `b7f9d0a3` |
| runner:1034 | B101 | E | 1032 | `b7f9d0a3` |
| runner:1101 | B101 | E | 1099 | `877dd64f` |
| runner:1165 | B101 | E | 1163 | `b7f9d0a3` |
| runner:1308 | B101 | E | 1306 | `b33a4b6e` |
| runner:1351 | B101 | E | 1349 | `13a7a63f` |
| runner:1373 | B101 | E | 1371 | `216377f4` |
| runner:1463 | B101 | E | 1453 | `b33a4b6e` |
| runner:1478 | B101 | E | 1468 | `b7f9d0a3` |
| runner:1538 | B101 | E | 1528 | `f02ca5c3` |
| runner:1629 | B101 | E | 1619 | `f02ca5c3` |
| runner:1631 | B101 | E | 1621, 1629, 1633 | `f02ca5c3` |
| runner:1632 | B101 | E | 1622 | `f02ca5c3` |
| runner:1639 | B101 | E | 1621, 1629, 1633 | `409939ff` |
| runner:1640 | B101 | E | 1630 | `409939ff` |
| runner:1643 | B101 | E | 1621, 1629, 1633 | `a6e9ff69` |
| runner:1644 | B101 | E | 1634 | `a6e9ff69` |
| runner:1674 | B101 | E | 1664, 2083, 2251 | `414a381e` |
| runner:1675 | B101 | E | 1665 | `414a381e` |
| runner:1695 | B101 | E | 1685, 1705 | `414a381e` |
| runner:1715 | B101 | E | 1685, 1705 | `414a381e` |
| runner:2001 | B101 | E | 1991 | `b7f9d0a3` |
| runner:2002 | B101 | E | 1992 | `b7f9d0a3` |
| runner:2093 | B101 | E | 1664, 2083, 2251 | `94a528c7` |
| runner:2173 | B101 | E | 2163 | `191b1330` |
| runner:2261 | B101 | E | 1664, 2083, 2251 | `414a381e` |
| runner:2282 | B101 | E | 2272 | `b7f9d0a3` |
| runner:2285 | B101 | E | 2275 | `b7f9d0a3` |
| runner:2313 | B101 | E | 2303 | `b7f9d0a3` |
| runner:2317 | B101 | E | 2307 | `b7f9d0a3` |
| runner:2354 | B101 | E | 2344 | `191b1330` |
| runner:2440 | B101 | E | 2430 | `386fbf4c` |
| runner:2458 | B101 | E | 2448 | `191b1330` |
| runner:2551 | B101 | E | 2541 | `7e41ad8e` |
| runner:2637 | B101 | E | 2627 | `7e41ad8e` |
| runner:2650 | B101 | E | 2640 | `fd0e9170` |
| runner:2687 | B101 | E | 2676 | `7e41ad8e` |
| runner:2698 | B101 | E | 2687 | `972ce20c` |
| runner:2706 | B101 | E | 2695 | `972ce20c` |
| runner:2707 | B101 | E | 2696 | `972ce20c` |
| runner:2708 | B101 | E | 2697 | `972ce20c` |
| runner:2713 | B101 | E | 2702 | `972ce20c` |
| runner:2714 | B101 | E | 2703 | `972ce20c` |
| runner:2716 | B101 | E | 2705 | `972ce20c` |
| runner:2723 | B101 | E | 2712 | `972ce20c` |
| runner:2724 | B101 | E | 2713 | `972ce20c` |
| runner:2758 | B101 | C | 2676 | `3b6ecbe7` |
| runner:2769 | B101 | C | 2687 | `3b6ecbe7` |
| runner:2777 | B101 | C | 2695 | `3b6ecbe7` |
| runner:2778 | B101 | C | 2696 | `3b6ecbe7` |
| runner:2779 | B101 | C | 2697 | `3b6ecbe7` |
| runner:2784 | B101 | C | 2702 | `3b6ecbe7` |
| runner:2785 | B101 | C | 2703 | `3b6ecbe7` |
| runner:2787 | B101 | C | 2705 | `3b6ecbe7` |
| runner:2796 | B101 | C | 2712 | `3b6ecbe7` |
| runner:2797 | B101 | C | 2713 | `3b6ecbe7` |
| runner:2923 | B101 | E | 2825 | `ec3de5a2` |
| runner:2924 | B101 | E | 2826 | `ec3de5a2` |

## 4. 패키지 감사

건수는 원본 pip-audit의 경고 레코드 수와 동일 ID를 중복 제거한 수를 구분한다.
서로 다른 ID의 alias까지 통합한 CVE 수는 아니다. 패키지별 수정 버전은 해당 경고가 제시한 값이다.
하나의 버전이 모든 경고와 현재 엔진 호환성을 동시에 해결한다는 뜻이 아니다.
심각도는 [OSV API](https://google.github.io/osv.dev/api/#operation/GetVuln)의 공식 advisory를 조회했다.
라벨이 없는 23개 고유 ID는 원본 CVSS 벡터를 QA 전용 [cvss 3.6](https://pypi.org/project/cvss/)으로 계산했다.
GHSA 조회가 실패한 항목은 원본 PYSEC ID로 보완했다. 최종 심각도 미판정은 0건이다.
계산 벡터·등급·advisory URL은 `dependency_review_after.json`에 있다. pip-audit 원본에는 심각도 필드가 없다.

### 4.1 납품 범위: 도구 venv

| 패키지 | 이전 → 새 버전 | 새 버전 릴리스 | 원본 경고 → 재검사 | 원본 최고 확인 심각도 |
|---|---|---|---|---|
| fonttools | 4.60.1 → 4.65.0 | 2026-09-10 | 1 → 0 | MODERATE |
| Pillow | 12.0.0 → 12.3.0 | 2026-07-01 | 76(고유 ID 58) → 39(고유 ID 39) | CRITICAL |
| pip | 22.0.2 → 26.2.2 | 2026-10-20 | 14(고유 ID 7) → 0 | MODERATE |
| setuptools | 59.6.0 → 84.2.1 | 2026-10-20 | 9(고유 ID 5) → 0 | HIGH |

전체 15개 배포 패키지의 원본 100건(고유 ID 71건) → 39건이다.
`pip_audit_tools_after.json`에는 Pillow 외 경고·감사 skip이 없고 `pip check`도 통과했다.
단, wheel 내부에 vendoring된 모든 라이브러리를 별도 패키지로 감사한 결과는 아니다.
모든 갱신 버전은 기준일보다 14일 이상 전에 공개됐다.
릴리스 날짜·Python 요구 버전·wheel SHA256의 근거는
[fonttools](https://pypi.org/pypi/fonttools/4.65.0/json),
[Pillow](https://pypi.org/pypi/pillow/12.3.0/json),
[pip](https://pypi.org/pypi/pip/26.2.2/json),
[setuptools](https://pypi.org/pypi/setuptools/84.2.1/json)의 PyPI 메타데이터이며 고정값은 `versions.env`에 있다.
fonttools의 더 새 버전은 Python 조건 또는 14일 조건에서 제외했고 pip 26.3은 14일 미경과로 제외했다.

Pillow 예외는 사용자 승인 사항이다. 워크스테이션·CUDA·RBLN은 Python 3.10이며
[Pillow 13.0.0 메타데이터](https://pypi.org/pypi/pillow/13.0.0/json)의 요구 조건은 Python 3.11 이상이다.
12.3.0 잔여 경고 39건의 수정 버전은 모두 13.0.0이다. 12.x 대체 수정판은 확인되지 않았다.
Python 3.11 이상 환경으로 옮길 때 13.x로 갱신하고 다시 감사한다.

| 이미지 입출력 경로 확인 | 실제 사용·노출 판단 |
|---|---|
| `report_figures.py:15,70,268` | 내부 결과 CSV·JSON을 읽음. 이미지 파일 입력 API 없음 |
| `report_figures.py:96` | matplotlib Agg 그림을 `savefig(...png)`로 저장. 외부 이미지 열기·해석 없음 |
| `operator_stats.py:58,93,156` | gzip/JSON/Perfetto trace와 meta 입력, CSV·Markdown·JSON 출력. Pillow·이미지 입력 없음 |
| 잔여 판단 | 외부 이미지 디코더의 공격 입력 경로는 현재 도구에서 확인되지 않음. 일부 advisory는 인코더·폰트·메모리 연산도 포함하므로 모든 39건이 도달 불가라고 단정하지 않음 |

내부 측정 데이터·설정·폰트만 사용한다는 운영 전제가 깨지면 재검토한다.
이번 기준은 **Pillow 제외 0건**이며 전체 venv가 취약점 0건이라는 표현을 사용하지 않는다.

### 4.2 납품 범위 밖: CUDA·RBLN

원본 `pip_audit_cuda.json`은 201개 패키지 중 16개에서 171건(고유 ID 155건),
`pip_audit_rbln.json`은 198개 중 16개에서 104건(고유 ID 100건)을 보고했다.
환경을 수정하지 않았다. 최고 심각도는 확인한 advisory 라벨과 보완 계산 등급 중 최댓값이다.

| 환경·패키지(버전) | 경고/고유 ID | 최고 확인 심각도 | 감사가 제시한 수정 버전 | 노출·권고 |
|---|---:|---|---|---|
| CUDA aiohttp 3.14.3 | 8/8 | HIGH | 3.14.4 | N |
| CUDA certifi 2026.7.22 | 2/1 | CRITICAL | 2026.10.18 | N |
| CUDA diskcache 5.6.3 | 2/1 | MODERATE | 없음 | F |
| CUDA dnspython 2.8.0 | 1/1 | HIGH | 2.9.0 | N |
| CUDA filelock 3.32.5 | 12/12 | HIGH | 4.0.9, 4.2.1 | F |
| CUDA mcp 2.1.1 | 4/4 | MODERATE | 1.30.0, 2.2.0 | M |
| CUDA multidict 6.7.1 | 1/1 | MODERATE | 6.9.1 | N |
| CUDA opentelemetry-api 1.44.0 | 1/1 | MODERATE | 1.45.1 | O |
| CUDA pillow 12.3.0 | 39/39 | CRITICAL | 13.0.0 | I |
| CUDA pyjwt 2.13.0 | 15/15 | CRITICAL | 2.14.0, 2.15.0; 일부 없음 | M |
| CUDA setuptools 81.0.0 | 3/2 | MODERATE | 83.0.0, 84.1.0 | B |
| CUDA torch 2.11.0 | 1/1 | LOW | 2.13.0 | L |
| CUDA transformers 4.57.6 | 9/6 | HIGH | 5.0.0, 5.0.0rc3, 5.3.0, 5.5.0, 5.10.0; 일부 없음 | L |
| CUDA urllib3 2.7.0 | 3/3 | HIGH | 2.8.0 | N |
| CUDA uv 0.12.9 | 2/2 | CRITICAL | 0.12.18, 0.13.4 | B |
| CUDA vllm 0.22.0 | 68/58 | HIGH | 0.22.1, 0.24.0, 0.25.0, 0.26.0, 0.27.0, 0.28.0, 0.29.0, 0.30.0, 0.31.0, 0.32.0; 일부 없음 | V |
| RBLN accelerate 1.14.0 | 1/1 | MODERATE | 없음 | L |
| RBLN aiohttp 3.14.3 | 8/8 | HIGH | 3.14.4 | N |
| RBLN certifi 2026.7.22 | 2/1 | CRITICAL | 2026.10.18 | N |
| RBLN diskcache 5.6.3 | 2/1 | MODERATE | 없음 | F |
| RBLN dnspython 2.8.0 | 1/1 | HIGH | 2.9.0 | N |
| RBLN filelock 3.32.5 | 12/12 | HIGH | 4.0.9, 4.2.1 | F |
| RBLN mcp 2.1.1 | 4/4 | MODERATE | 1.30.0, 2.2.0 | M |
| RBLN multidict 6.7.1 | 1/1 | MODERATE | 6.9.1 | N |
| RBLN opentelemetry-api 1.44.0 | 1/1 | MODERATE | 1.45.1 | O |
| RBLN pillow 12.3.0 | 39/39 | CRITICAL | 13.0.0 | I |
| RBLN pyjwt 2.13.0 | 15/15 | CRITICAL | 2.14.0, 2.15.0; 일부 없음 | M |
| RBLN setuptools 77.0.3 | 5/3 | HIGH | 78.1.1, 83.0.0, 84.1.0 | B |
| RBLN tornado 6.5.8 | 6/6 | HIGH | 6.5.9, 6.6 | T |
| RBLN transformers 5.8.1 | 2/2 | HIGH | 5.10.0; 일부 없음 | L |
| RBLN urllib3 2.7.0 | 3/3 | HIGH | 2.8.0 | N |
| RBLN uv 0.12.9 | 2/2 | CRITICAL | 0.12.18, 0.13.4 | B |

RBLN에서 `rebel-compiler`, `torch`, `torchaudio`, `torchcodec`, `torchvision`, `vllm`은
PyPI에 일치하는 배포판이 없어 감사에서 skip됐다. 로컬 CPU 빌드·벤더 패키지의 skip을 0건으로 해석하지 않는다.
SDK·드라이버·all-smi/Collector/TP 바이너리의 전이 의존성 전체에 대한 취약점 스캔도 이번 pip-audit 범위가 아니다.

노출·권고 코드의 의미는 다음과 같다. 이는 도구 코드의 사용 경로 판단이며 실제 공격 재현 시험은 아니다.

| 코드 | 사용 방식·노출 | 운영 권고 |
|---|---|---|
| N | aiohttp·multidict·dnspython·urllib3·certifi: 로컬 HTTP 및 엔진의 전이 의존성. DNS·외부 TLS 사용 여부는 전체 SDK 실행까지 확인하지 않음 | 외부 요청·모델 원격 다운로드 차단, 엔진 호환 수정 버전 별도 검증 |
| M | mcp·pyjwt: 프로파일러가 MCP 서버나 JWT 인증 API를 직접 사용하지 않음. vLLM 전이 기능 도달 여부 미확인 | 불필요한 외부 API 비활성화, 서비스 개방 전 해당 기능 재검토 |
| F | diskcache·filelock: 캐시·파일을 엔진이 사용. 비신뢰 사용자가 쓸 수 있는 캐시는 로컬 공격 경로 | 캐시 소유자·권한 제한, 디렉터리 공유 최소화 |
| O | opentelemetry-api: trace 모드에서 사용, 로컬 Collector 수출 | OTLP 포트 외부 접근 차단, 서버·Collector 호환 갱신 검증 |
| I | Pillow: 도구의 사용 경로는 4.1 참조. CUDA·RBLN의 멀티모달 전이 경로는 도구와 같다고 단정할 수 없음 | 텍스트 전용 실험 유지, 외부 이미지 입력 금지, Python 이전 시 갱신 |
| B | setuptools·uv: 설치·빌드 도구. 측정 경로에서 직접 패키지 설치 안 함 | 신뢰하는 고정 배포물만 설치, 별도 복제 venv에서 갱신 검증 |
| L | torch·transformers·accelerate: 모델 로딩·추론에 사용. 신뢰하는 로컬 모델이 전제 | 비신뢰 모델·pickle·플러그인 금지, 모델 파일 해시·권한 관리 |
| V | vLLM: 실제 서비스 사용. 생성된 서버·proxy는 127.0.0.1, API 인증을 대신하지 않음 | 외부 개방 금지, 프롬프트·모델·서비스 설정 신뢰, 팀이 수정 버전·RBLN 호환성 검증 |
| T | tornado: 프로파일러에서 직접 서버를 열지 않음. 전체 전이 사용 여부 미확인 | 사용 기능 조사 후 수정 버전 검증, 불필요한 웹 서비스 종료 |

## 5. 비밀정보·절대경로 점검

최초 `secrets_grep.txt`의 8개 결과는 수동 검토했다. 실제 인증 비밀 발견은 0건이다.
검토 대상은 지표의 token 단위, 합성 fixture 설명 두 줄, `one_token` 시험,
하네스의 실행 구분용 `run_token`, tokenizer 입력, 첫 토큰 시각, 토큰당 에너지다.
`run_token`은 시각·PID 기반 실행 구분값이며 접근 권한 토큰이 아니다.
`abs_path_grep.txt`는 비어 있었다. 패턴 일치가 없다는 사실만으로 모든 경로나 비밀의 부재를 보장하지 않는다.
재검사 범위·패턴·일치 위치는 `grep_after.json`에 보존한다. 문서의 점검 용어 자체 일치는 코드와 구분한다.
재검사는 시스템 경로 접두사까지 넓혀 셸 스크립트 두 개의 첫 줄과 하네스 감사 스크립트의
표준 env shebang 한 줄, 총 3건을 확인했다. 모두 기존 인터프리터 지정이며 사용자 설치 경로가 아니다.
비밀 할당 형태의 7건은 위 token 관련 자료의 부분집합이고, 개인키·서비스 키 패턴은 0건이었다.
환경 파일과 CUDA·RBLN·도구 Python 경로 값은 이번 문서·저장소 파일에 옮겨 적지 않았다.

## 6. 재검사와 남은 확인

| 검사 | 결과·근거 |
|---|---|
| v2 번들·설치 | 15개 wheel, 고정 SHA256·번들 manifest 검증, 오프라인 bootstrap 후 런타임 설치 |
| 도구 버전 | all-smi 0.28.1, Collector 0.163.2, TP 58.2 확인; 서비스 기동 없음 |
| 단위시험 | `unittest_hetero_after.txt`, `unittest_pdd_after.txt` 참조 |
| 새 venv 스모크 | 기존 시험 실행기에서 `PDD_TOOLS_PY`만 v2로 지정; 합성 PB 읽기·9개 그림 생성. v2 자체의 합성 GPU trace CLI도 통과(`tools_smoke_after.json`) |
| 시험 환경 구분 | 도구 venv만으로 전체 연산자 시험을 import하면 분석 의존성 `prometheus_client`가 없음. 분석 시험은 시스템 Python, 실제 도구 subprocess는 v2로 분리 |
| 스타일·헤더 | AGENTS의 변경·신규 파일 대상 pre-commit 결과는 `pre_commit_after.txt` 참조 |
| 잔여 운영 확인 | all-smi 방화벽·결과 ACL·네트워크 송신 관찰, 벤더/로컬 빌드 감사, 포함 라이브러리의 재배포 고지 검토 |

새 환경 적용은 운영자가 `PDD_TOOLS_PY`를 v2 도구 venv의 Python으로 바꿔 수행한다.
기존 실행 환경·환경 파일은 수정하지 않았다. 실측 재실행·GPU/NPU 부하 작업은 하지 않았다.

## WP8 추가 정적 점검(2026-11-13)

| 대상 | 검사·판단 | 결과 |
|---|---|---|
| profiler/perfetto_timeline.py | Bandit JSON·텍스트, nosec 없음 | High/Medium/Low 각 0, 분석 제외 0 |
| 입출력 | 사용자가 지정한 기존 측정 JSONL·Prometheus 원문 읽기, 저장소 밖 pftrace·검증 JSON 쓰기 | 측정 경로·서버 설정 변경 없음 |
| 외부 도구 | 환경의 PERFETTO_TP_BIN을 TraceProcessorConfig(bin_path=...)로 지정 | 셸 조립/eval 없음; 신뢰한 로컬 실행 파일을 지정 |
| UI | install_offline의 127.0.0.1 HTTP 정적 파일 서비스 사용 안내 | 외부 바인드 추가 없음, 화면·실제 네트워크 동작은 수행자 확인 |
| 추가 의존성 | 기존 분석 파서 재사용을 위해 도구 venv에 prometheus-client==0.26.0 설치 | CUDA·RBLN 및 versions.env/기존 번들은 변경하지 않음; v2 재설치 시 별도 wheel 필요 |

근거: 로컬 작업 기록 `.notes/wp8_bandit.json`, `.notes/wp8_bandit.txt`.
이번 Bandit 0건을 의존 패키지 전체 취약점 0건으로 확대하지 않는다.
추가 패키지의 pip-audit와 최종 번들 반영은 별도 납품 재검사 항목이다.
