---
name: api-mock-generator
description: "엑셀에서 복사한 API 명세 텍스트(탭 구분)를 파싱하여 Request/Response Mock JSON 데이터를 생성한다. 트리거 키워드: mock 생성, mock data 생성, api mock, mock json, 목 데이터 생성, 테스트 데이터 생성, api 명세로 mock, 명세 붙여넣기. 엑셀 복사붙여넣기 형태의 API 명세가 포함된 모든 요청에 사용한다."
---

## 워크플로우

1. 사용자가 붙여넣은 엑셀 텍스트에서 Request / Response 섹션 식별
2. 각 섹션의 필드를 파싱하여 계층 구조 파악
3. Mock JSON 생성 후 출력

섹션이 여러 개(예: Response 2개)인 경우 각각 별도로 생성한다.

## 파싱 규칙

컬럼 형식 상세 및 예시는 `references/excel-format.md` 참고.

### 섹션 구분

탭이 없는 제목 행으로 구분:
- `응답(Response) 인터페이스 항목` → Response
- `요청(Request) 인터페이스 항목` → Request

### 계층 구조

영문 필드명(snake_case)의 컬럼 위치로 판별:
- `cols[3]`에 영문명 → 최상위 필드 (indent 0)
- `cols[4]`에 영문명 → 자식 필드 (indent 1, 직전 List/Object의 하위)
- `cols[5]`에 영문명 → 손자 필드 (indent 2)

### 스킵 대상

- `순번` 컬럼이 숫자가 아닌 행 (헤더, 제목)
- `구분`이 `Header`인 행 (공통헤더는 별도 처리)

### 예시값 추출 우선순위

1. 입력값(예시) 컬럼의 첫 줄 사용
2. `: ` 포함 시 앞부분만 (예: `0 : 무료` → `"0"`)
3. `null` 단독이면 JSON null
4. 없으면 필드명 패턴 기반 기본값 생성

## Mock 생성 규칙

### 공통 응답 래퍼 (Response 전체에 적용)

**Response**는 항상 아래 공통 래퍼로 감싸서 출력한다.

- 정상 응답(성공): `"result": true`, `"data.succeed": true`
- 오류 응답(실패): `"result": false`, `"data.succeed": false`, `"message"`: 오류 메시지

```json
{
  "code": 200,
  "result": true,
  "message": "success",
  "desc": null,
  "iat": 1773817173616,
  "data": {
    "succeed": true,
    "...필드 또는 list..."
  },
  "messages": null
}
```

- `iat`: 현재 시각 밀리초 타임스탬프 (임의값 사용)
- `data` 내부에 명세의 Body 필드를 배치
- 배열 필드명이 명세에 `data`로 되어 있어도, 실제 키는 `list`로 출력 (예: `"data": { "succeed": true, "list": [...] }`)

오류 응답 예시:
```json
{
  "code": 200,
  "result": false,
  "message": "오류 메시지",
  "desc": null,
  "iat": 1773817173616,
  "data": {
    "succeed": false,
    "err_cd": "E001",
    "err_msg": "요청 처리 중 오류가 발생했습니다."
  },
  "messages": null
}
```

**Request**는 기존과 동일하게 body 내용만 출력한다.

| 타입 | 처리 |
|------|------|
| `List` / 반복여부=Y | 자식 필드로 구성된 배열 **2개 항목** 생성 |
| `Object` | 자식 필드로 구성된 객체 |
| `String` / `Integer` | 예시값 or 필드명 패턴 기반값 |

### 필수여부=N 처리 규칙

- **리스트 항목 내 필드**: 1번째 항목 → 값 채움 / 2번째 항목 → `null`
- **최상위(비리스트) 필드**: 필수여부와 관계없이 값 채움

## 스크립트 실행 (복잡한 명세에 선택 사용)

의존성(`openpyxl`)은 첫 실행 시 자동 설치된다.

```bash
# TSV 텍스트 파일
python3 ~/.claude/skills/api-mock-generator/scripts/generate_mock.py spec.txt

# stdin
cat spec.txt | python3 ~/.claude/skills/api-mock-generator/scripts/generate_mock.py

# xlsx 파일 (전체 시트)
python3 ~/.claude/skills/api-mock-generator/scripts/generate_mock.py spec.xlsx

# xlsx + API 번호 필터링
python3 ~/.claude/skills/api-mock-generator/scripts/generate_mock.py spec.xlsx --api "API-001"

# xlsx + 시트명 지정
python3 ~/.claude/skills/api-mock-generator/scripts/generate_mock.py spec.xlsx --sheet "단위서비스명세" --api "API-001"
```

스크립트 결과를 기반으로 구분자 필드, 특수 포맷 등을 추가 보정한다.

### xlsx 파일 처리 시 워크플로우

1. 사용자가 xlsx 파일 경로와 API 번호를 제공
2. 스크립트로 해당 API 섹션만 추출 → TSV 변환
3. 기존 파싱 로직으로 Mock JSON 생성

## 출력 형식

각 섹션별 JSON 코드 블록 + 아래 설명:
- 선택 필드(`필수=N`) 중 null 처리된 항목
- 구분자 포맷 등 특수 처리 사항
- 복수 Response인 경우 `Response 1`, `Response 2`로 구분
