# Qwen API 연결 검증 · 2026-09-18

## 범위

기존 공통 앱의 개선안 생성·수정본 검토에 `IMPROVEMENT_PROVIDER=qwen`을 추가했습니다.
문서 분석은 기존 `LLM_PROVIDER=local`을 유지합니다. parser, OCR, UI, navigation은 수정하지 않았습니다.
미국·한국 모두 같은 provider를 사용하며 명시적인 Qwen 선택을 KR Azure 설정이 덮어쓰지 않습니다.

Model Studio의 `/chat/completions`로 관련 문맥과 엄격한 JSON Schema를 보냅니다.
응답은 기존 Pydantic 및 근거 ID·인용문 검사에 그대로 통과해야 합니다.
키/모델/주소 누락, 권한, 한도, 네트워크 오류, JSON 형식 오류, 출력 중단을 성공으로 숨기지 않습니다.
자동 재시도나 다른 유료 모델로의 전환은 없습니다. 원본 문서/분석을 변경하지 않습니다.

## 검증 결과

- Qwen 전용 테스트: 26개 통과. HTTP 응답을 대체한 연결/오류 처리 테스트입니다.
- 미국 합성 사례와 실제 한국 출원 10-2019-0000844의 공통 API 개선안·수정본 요청 통과.
- 실제 한국 PDF/XML에서 구성한 문맥, 근거 보존, 분석 데이터 불변 확인.
- 전체 회귀 `uv run python -m pytest -q`: **353 passed**, 86.42초. 기존 라이브러리 deprecation 경고 2개.
- `uv run python -m ruff check .`: 통과.
- `uv run python -m ruff format --check .`: 통과, 187개 파일.
- 실제 자료 preflight: 한국 출원 10-2019-0000844는 근거 9개/직렬화 문맥 15,391자,
  미국 14/623,904의 저장 분석 Claim 1/R1은 근거 7개/19,742자를 구성했습니다.
  두 실행 모두 키/모델 설정 누락을 감지하고 외부 요청 전에 중단했습니다.
  기록은 `data/outputs/qwen/20260918T035653251767Z/report.json` 및
  `data/outputs/qwen/20260918T035741927663Z/report.json`입니다.
- **실제 Qwen 호출: 미검증.** 검사 당시 루트/한국 `.env` 및 환경변수에 Qwen 키가 없었습니다.
- **개선안·수정본 판단의 품질: 미검증.** 테스트용 답변은 Qwen이 생성한 답변이 아닙니다.
- 새로운 브라우저 테스트는 수행하지 않았습니다. 이번 변경에 frontend 파일은 없습니다.

## 재현

```powershell
uv run python -m pytest tests/test_qwen_provider.py -q
uv run python -X utf8 -m scripts.validate_qwen
```

두 번째 명령은 실제 한국 자료로 문맥을 만든 뒤 설정을 확인합니다. 키가 없으면 종료 코드 2와
`BLOCKED_OR_FAILED`로 기록하고 API를 호출하지 않습니다. 키가 있어도 `--live` 없이는 호출하지 않습니다.
키/리전 주소/모델 설정 후 `--live`를 추가하면 개선안 및 원문과 동일한 청구항의 검토를
최대 2회 요청합니다. 이는 연결·근거 검사이며 보정안의 적절성 평가는 아닙니다.
`--revised-file`로 별도 수정안을 시험할 수 있습니다. 설정은 루트 README를 참고하세요.

## 이번 작업의 수정 파일

- `backend/config.py`: Qwen 검토 설정
- `backend/improvements/providers.py`: Qwen HTTP provider
- `backend/improvements/service.py`: 선택 및 한국 모드 설정 우선순위
- `tests/test_qwen_provider.py`: 연결·실패·근거 검사 회귀
- `scripts/validate_qwen.py`: 실제 자료 설정 검사 및 명시적 API 테스트
- `.env.example`, `README.md`, `QWEN_API_VALIDATION.md`: 설정과 검증 안내

기존 작업의 미커밋 수정은 유지했습니다. 실제 `.env`의 키나 기본 provider는 변경하지 않았습니다.
