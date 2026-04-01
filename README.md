# api-mock-generator

엑셀 API 명세를 붙여넣으면 Request/Response Mock JSON을 자동 생성하는 Claude Code 커스텀 스킬.

## 개요

엑셀에서 복사한 탭 구분 API 명세 텍스트를 파싱하여 Mock JSON 데이터를 생성한다.  
복잡한 명세는 Python 스크립트(`generate_mock.py`)를 통해 xlsx 파일 직접 처리도 지원한다.

## 트리거 키워드

Claude에게 아래 키워드가 포함된 메시지를 보내면 자동으로 이 스킬이 활성화된다.

```
mock 생성 / mock data 생성 / api mock / mock json
목 데이터 생성 / 테스트 데이터 생성 / api 명세로 mock / 명세 붙여넣기
```

## 사용법

### 1. 엑셀 텍스트 붙여넣기 (기본)

엑셀에서 API 명세 셀을 선택 후 복사(Ctrl+C) → Claude 채팅창에 바로 붙여넣기

```
명세 붙여넣어줄게, mock json 만들어줘

[엑셀 텍스트 붙여넣기]
```

### 2. Python 스크립트 (복잡한 명세)

```bash
# TSV 텍스트 파일
python3 scripts/generate_mock.py spec.txt

# stdin
cat spec.txt | python3 scripts/generate_mock.py

# xlsx 파일 (전체 시트)
python3 scripts/generate_mock.py spec.xlsx

# xlsx + API 번호 필터링
python3 scripts/generate_mock.py spec.xlsx --api "API-001"

# xlsx + 시트명 지정
python3 scripts/generate_mock.py spec.xlsx --sheet "단위서비스명세" --api "API-001"
```

> 의존성(`openpyxl`)은 첫 실행 시 자동 설치된다.

## 출력 형식

### Response (공통 래퍼 적용)

```json
{
  "code": 200,
  "result": true,
  "message": "success",
  "desc": null,
  "iat": 1773817173616,
  "data": {
    "succeed": true,
    "list": [ ... ]
  },
  "messages": null
}
```

- `result: false` 오류 응답도 함께 생성
- 명세의 배열 필드명이 `data`여도 실제 키는 `list`로 출력

### Request

Body 필드만 출력 (래퍼 없음)

## 파싱 규칙 요약

| 항목 | 규칙 |
|------|------|
| 섹션 구분 | 탭 없는 제목행으로 Request/Response 구분 |
| 계층 구조 | 영문명 컬럼 위치(3/4/5)로 최상위/자식/손자 판별 |
| 예시값 | 첫 줄 사용, `: ` 포함 시 앞부분만, `null` 단독이면 JSON null |
| List 타입 | 자식 필드로 배열 2개 항목 생성 |
| 필수여부=N | 리스트 내 2번째 항목은 null 처리 |
| Header 구분 | `구분=Header` 행은 스킵 |

필드명 패턴 기반 기본값, 컬럼 구조 상세는 [`references/excel-format.md`](references/excel-format.md) 참고.

## 디렉토리 구조

```
api-mock-generator/
├── SKILL.md                  # 스킬 정의 (워크플로우, 파싱/생성 규칙)
├── requirements.txt          # Python 의존성 (openpyxl)
├── scripts/
│   └── generate_mock.py      # xlsx/TSV 처리 스크립트
└── references/
    └── excel-format.md       # 엑셀 컬럼 구조 및 파싱 규칙 상세
```

## 설치

```bash
# Claude Code 스킬 디렉토리에 복사
cp -r api-mock-generator ~/.claude/skills/
```
