# 설치 안내서

문서 갱신: 2026-11-11. 아래 시험·자료 확인일은 2026-11-10이다.

기준: 2026-11-10, v1.0.0-rc1 독립 설치 시험(IT-03).
명령은 저장소 루트 기준이며 대문자 변수의 실제 값은 운영자가 저장소 밖 환경 파일에 설정한다.
아래 순서는 IT-03의 패키지 검증·clone·설치·S1 확인 순서다.
설치 실행 자체는 수행자 확인이며, 현재 설치물·해시·태그·시험 결과는 직접 재확인했다.

## 전제 환경

| 항목 | 준비 사항·근거 |
|---|---|
| OS·Python | Linux x86_64, 번들 python-version과 같은 Python 3.10; venv 지원 |
| 장치 | 실측은 NVIDIA RTX PRO 6000 Blackwell 1장, RBLN-CA22 2장. 다른 장비는 별도 검증 필요 |
| 드라이버·SDK | nvidia-smi, rbln-smi가 정상 동작하는 기존 환경; 번들이 드라이버를 설치하지 않음 |
| CUDA·RBLN venv | 호환 vLLM 0.22.0 및 해당 장치 의존성 사전 설치. CUDA_PY·RBLN_PY 지정 |
| 모델 | 로컬 모델·토크나이저·config·가중치 준비. S1은 Qwen3-0.6B FP16 |
| 시험 의존성 | 시스템 Python의 prometheus_client; PyYAML 없으면 YAML 시험 skip. 도구 venv를 엔진 venv로 사용하지 않음 |
| 공간·권한 | clone·모델·번들·도구·결과·캐시를 구분하고 설치/결과를 저장소 밖에 둠 |

정확한 드라이버·SDK 호환 조합은 수령 환경의 공급자 설치 지침과 서비스 config.json을 확인한다.
본 문서는 모든 드라이버 버전의 호환성을 보증하지 않는다.

## 1. 패키지 무결성과 소스

PACKAGE, CLONE_DIR, RELEASE_TAG를 지정한다. IT-03의 RELEASE_TAG는 v1.0.0-rc1이었다.

```bash
(cd "$PACKAGE" && sha256sum --check MANIFEST.sha256)
git clone --branch main "$PACKAGE/repo.bundle" "$CLONE_DIR"
git -C "$CLONE_DIR" checkout --detach "$RELEASE_TAG"
git -C "$CLONE_DIR" rev-parse HEAD "refs/tags/$RELEASE_TAG^{commit}"
```

해시 오류가 있으면 설치를 중단하고 전달 원본을 확인한다. 두 커밋과 RELEASE_NOTES.md의 커밋이 일치해야 한다.
IT-03에서는 HEAD·태그가 b82425592da29133c91b4df24169c4cda04641ee로 일치했다.
새 문서는 rc1 태그에 자동 포함되지 않으므로 최종 납품 시 새 태그·패키지를 만든다.

## 2. 오프라인 도구 설치

TOOLS_VENV·TOOLS_DIR은 저장소 밖 새 위치다. 원래 CUDA·RBLN venv를 덮어쓰지 않는다.

```bash
bash "$CLONE_DIR/tools/hetero/third_party/install_offline.sh"   --bundle "$PACKAGE/offline_bundle" --venv "$TOOLS_VENV" --tools-dir "$TOOLS_DIR"
```

스크립트는 SHA256SUMS·versions.env·산출물 해시와 Python 버전을 검사한 뒤 venv를 만든다.
pip·setuptools를 로컬 wheel로 먼저 갱신하고 고정 requirements를 no-index로 설치한다.
all-smi·Collector·trace_processor_shell·Perfetto UI를 배치하고 바이너리 버전을 확인한다.
별도 시험 의존성·드라이버·모델·엔진은 이 번들 설치 범위가 아니다.

| IT-03 도구 venv에서 직접 조회한 패키지 | 버전 |
|---|---|
| perfetto / matplotlib | 0.58.2 / 3.10.9 |
| Pillow / fonttools | 12.3.0 / 4.65.0 |
| pip / setuptools | 26.2.2 / 84.2.1 |

Pillow 잔여 보안 경고·Python 3.10 제약은 [보안 점검표](security_check.md)를 따른다.
납품 라이선스·소스 제공 안내는 [제3자 라이선스](third_party_licenses.md)를 함께 확인한다.

## 3. 환경 파일

설치기가 출력한 export 값을 저장소 밖 신뢰할 수 있는 환경 파일에 반영한다.
경로 값은 문서·git에 넣지 않는다. 아래는 실제 경로 대신 자리표시자를 쓴 구성 예다.

```bash
export CUDA_PY='<CUDA venv Python>'
export RBLN_PY='<RBLN venv Python>'
export PDD_TOOLS_PY='<도구 venv Python>'
export ALLSMI_BIN='<설치 위치>/all-smi'
export OTELCOL_BIN='<설치 위치>/otelcol-contrib'
export PERFETTO_TP_BIN='<설치 위치>/trace_processor_shell'
export QWEN06_PATH='<로컬 Qwen3-0.6B 모델>'
```

실행 셸에서 `source "$HETERO_ENV_FILE"`로 읽는다. 환경 파일을 임의 배포물에서 받아 실행하지 않는다.
이론 대역폭 변수는 확인된 장비 규격만 사용한다. 미설정이면 관련 비율은 not_collected다.

## 4. 설치 확인과 S1

```bash
cd "$CLONE_DIR"
git status --porcelain
"$PDD_TOOLS_PY" -c 'import matplotlib; from perfetto.trace_processor import TraceProcessor'
"$CUDA_PY" -c 'from tools.hetero.profiler.tools import check_tools; print(check_tools("deep"))'
python3 -m unittest discover -s tests/hetero
python3 -m unittest discover -s tests/pdd
"$CUDA_PY" -m tools.hetero.profiler.sweep   --scenarios "$S1_JSON" --sweep-dir "$S1_RESULTS"   --model "qwen3-0.6b=$QWEN06_PATH"
```

S1_JSON은 initial.json의 s1_b0·s1_pdd만 포함한 외부 JSON이다. IT-03은 각 176요청,
i512/o128, B0 슬롯 (1,1,1), PDD 동시성 2로 실행했다. 시작 전 장치 점유를 확인한다.
결과의 두 상태가 PASS인지, results.csv·comparison.csv가 생겼는지와 서비스 정지를 확인한다.
IT-03의 S1 10개 지표는 sweep2 대비 모두 ±10% 이내였다(최대 2.001%).
상세 판정·수치는 [시험 보고서](test_report.md), 실행·장애 처리는 [사용](user_guide.md)·[운영](operator_guide.md) 안내를 따른다.
