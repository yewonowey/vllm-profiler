# 제3자 소프트웨어·라이선스 목록

기준일: 2026-11-10. 납품하는 고정 도구 번들과 별도 실행 환경을 구분한다.
근거는 `tools/hetero/third_party/versions.env`, v2 번들의 LICENSE·NOTICE·`licenses/`,
결과 루트 `qa_20261110/licenses_tools_after.md`, `licenses_cuda.md`, `licenses_rbln.md`다.
패키지 메타데이터는 목록 작성의 출발점이며 최종 배포 조건은 동봉한 원문과 각 구성물의 조건을 따른다.

## 1. 납품 고정 바이너리

| 구성물 | 버전 | 확인한 프로젝트 라이선스 | 원문·출처 |
|---|---|---|---|
| all-smi | 0.28.1 | Apache-2.0 | [릴리스 LICENSE](https://github.com/lablup/all-smi/blob/v0.28.1/LICENSE), 번들 `artifacts/LICENSE.all-smi` |
| otelcol-contrib | 0.163.2 | Apache-2.0 | [릴리스 LICENSE](https://github.com/open-telemetry/opentelemetry-collector-releases/blob/v0.163.2/LICENSE), `artifacts/LICENSE.otelcol` |
| Perfetto trace_processor_shell·UI | 58.2 | Apache-2.0 | [릴리스 LICENSE](https://github.com/google/perfetto/blob/v58.2/LICENSE), `artifacts/LICENSE.perfetto` |

프로젝트 최상위 LICENSE 확인은 바이너리의 모든 전이 라이브러리 조사와 같지 않다.
all-smi archive의 AMD 보조 라이브러리, Collector의 포함 컴포넌트, Perfetto/UI의 포함 의존성은
최종 배포 전에 각 릴리스의 제3자 고지·구성 목록과 함께 추가 확인해야 한다.
현재 번들 NOTICE는 패키징 안내이며 upstream 고지 원문을 대체하는 법적 완결 선언이 아니다.

## 2. 도구 venv wheel 15개

라이선스는 설치된 배포판 메타데이터와 추출된 원문을 함께 확인했다.
`licenses_tools_after.md`는 pip·setuptools를 포함하도록 생성했다.

| 패키지 | 고정 버전 | 라이선스·주의 |
|---|---|---|
| perfetto | 0.58.2 | Apache-2.0 |
| matplotlib | 3.10.9 | PSF 기반 Matplotlib 라이선스, 포함 폰트 별도 고지 |
| contourpy | 1.3.2 | BSD-3-Clause |
| cycler | 0.12.1 | BSD-3-Clause |
| fonttools | 4.65.0 | MIT |
| kiwisolver | 1.5.1 | BSD-3-Clause |
| numpy | 2.2.6 | BSD-3-Clause; wheel 포함 라이브러리 고지 별도 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| Pillow | 12.3.0 | MIT-CMU; 포함 이미지 코덱의 조건 별도 |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 2.9.0.post0 | Apache-2.0 / BSD 계열, 파일별 원문 확인 |
| six | 1.17.0 | MIT |
| protobuf | 7.36.2 | BSD-3-Clause |
| pip | 26.2.2 | MIT; vendored 의존성별 원문 포함 |
| setuptools | 84.2.1 | MIT; vendored 의존성별 원문 포함 |

원문 보존 시 특히 확인할 항목은 다음과 같다.

| 구성 | 번들에서 확인한 고지 | 해석·배포 시 조치 |
|---|---|---|
| numpy | dist-info LICENSE와 random·ma 관련 LICENSE | 최상위 BSD만으로 OpenBLAS·LAPACK·GCC runtime 등 포함물 조건을 생략하지 않음 |
| matplotlib | dist-info LICENSE, DejaVu·STIX 폰트 LICENSE | 소프트웨어·동봉 폰트의 고지 함께 유지 |
| Pillow | dist-info `licenses/LICENSE` | MIT-CMU 원문과 포함 코덱 고지 유지. 보안 잔여 39건은 라이선스 허가와 별도 문제 |
| pip | wheel에서 LICENSE류 44개 파일 추출 | certifi 등 vendored 구성물의 서로 다른 조건도 보존 |
| setuptools | wheel에서 LICENSE류 19개 파일 추출 | 최상위 MIT 표기만 남기지 않고 각 포함물 원문 보존 |

실제 추출 원문에서 pip의 vendored certifi는 MPL-2.0, setuptools의
vendored autocommand 2.2.2는 LGPL-3.0, NumPy의 포함 GCC runtime은
GPL 및 GCC Runtime Library Exception 고지가 확인됐다.
setuptools의 validate_pyproject NOTICE에도 MPL 고지가 있다.
따라서 번들 전체를 MIT·BSD·Apache만으로 구성됐다고 표시해서는 안 된다.
최종 납품 전 해당 구성물의 소스 제공·고지·예외 적용 요건을 원문과 대조해야 하며,
이번 LICENSE 추출만으로 그 의무를 모두 충족했다고 판정하지 않았다.

번들 스크립트는 wheel 내부 경로에 LICENSE·LICENCE·COPYING·NOTICE가 포함된 파일을 추출한다.
이름 패턴에 맞지 않는 고지까지 모두 찾았다는 보장은 없으므로 재배포 검토 시 원본 archive도 확인한다.
반대로 SPDX 이름 목록처럼 경로가 패턴에 걸린 코드도 추출되므로 모든 추출 파일을 적용 라이선스로 세지 않는다.
도구가 참조하는 OS 한글 폰트는 wheel 목록과 별도다. 이번 납품은 생성된 PNG를 포함하며 OS 폰트 파일을 복사하지 않는다.
폰트 파일을 추가로 묶는 경우 해당 OS 패키지의 원문·재배포 조건을 확인해야 한다.

## 3. 번들 구성과 재현

| 파일·디렉터리 | 역할 |
|---|---|
| `versions.env` | 버전·릴리스 날짜·선정 이유·다운로드 URL·SHA256 고정 |
| `requirements.txt` | 런타임 wheel 13개 고정 |
| `bootstrap.txt` | pip·setuptools 고정 |
| `wheels/` | 대상 Python용 wheel 15개 |
| `artifacts/` | 바이너리 archive·프로젝트 LICENSE 원문 |
| `LICENSE` | 바이너리 프로젝트 LICENSE를 제목과 함께 결합 |
| `NOTICE` | 고정 릴리스·고지 위치 안내 |
| `licenses/` | wheel 안의 고지 원문을 패키지별 보존 |
| `SHA256SUMS` | 번들 파일 무결성 확인 |

설치는 manifest 검증, 저장소 고정값 대조, venv 생성, pip·setuptools 오프라인 갱신,
런타임 오프라인 설치, 바이너리 배치·버전 확인 순서다.
SHA256은 신뢰하는 고정값과의 동일성을 확인한다. 서명 검증·공급망 전체 검증을 대신하지 않는다.
갱신 시 버전·해시·라이선스·감사 결과를 함께 다시 만들고, 고지 파일을 삭제하지 않는다.

## 4. 별도 CUDA·RBLN 실행 환경

CUDA·RBLN venv, 드라이버, SDK, 모델 파일은 이 고정 도구 번들에 포함하지 않았다.
사용자는 해당 벤더·모델의 사용 및 배포 조건에 따라 별도로 설치한다.
`licenses_cuda.md`, `licenses_rbln.md`는 현재 환경의 목록이며 재배포 허가서가 아니다.

| 대상 | 확인된 메타데이터·남은 확인 |
|---|---|
| CUDA bindings·CUDA Python·NVIDIA runtime 계열 | NVIDIA LicenseRef 또는 Proprietary. 설치물 재배포 가능 범위를 별도 약관에서 확인 |
| CUDA의 cuda-toolkit, humming-kernels, openai-harmony, quack-kernels | 라이선스 메타데이터 UNKNOWN. 원문 확인 전 임의의 허용 라이선스로 분류하지 않음 |
| RBLN의 Intel compiler runtime·OpenMP | Proprietary 메타데이터. 실행 환경에만 존재하며 번들 제외 |
| RBLN의 openai-harmony | UNKNOWN. 원문 확인 필요 |
| RBLN SDK·컴파일러·로컬 빌드 vLLM/Torch | 별도 벤더/원 프로젝트 조건·추가 배포물 검토 필요. pip-licenses 자동 결과만으로 권한 확정 불가 |
| 모델 가중치·tokenizer | 모델별 원문·배포 정책 별도 확인. 코드의 Apache 표기로 모델까지 허가된다고 해석하지 않음 |

보안 취약점 목록·미감사 패키지·운영 권고는 [보안 점검 결과](security_check.md)에 있다.
실행 환경 패키지 버전과 라이선스는 환경 담당자가 갱신 시 다시 검토한다.

## 5. 저장소 코드 고지와 납품 확인

D5에 따라 `tools/hetero/`, `tests/hetero/` Python 첫 줄은 SPDX Apache-2.0 한 줄을 사용한다.
라이선스 헤더 훅에서 해당 경로가 제외된 것은 이 정책 때문이며 라이선스 의무의 면제가 아니다.
엔진 원본 헤더·toy proxy 원본 고지는 그대로 유지한다. 이동한 하네스의 출처와 기존 저작권 정보를 보존한다.
보안 경고 출처 구분은 새 라이선스 부여나 원저작권 양도를 의미하지 않는다.

최종 납품 시 코드·설치 bundle·그림·데이터 각각의 포함 목록과 SHA256을 대조하고,
원문 LICENSE·NOTICE·포함 의존성 고지가 빠지지 않았는지 확인한다.
UNKNOWN·벤더 독점 구성물·바이너리 전이 고지의 미확인 항목은 확인 전 납품 범위를 확대하지 않는다.
