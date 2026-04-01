#!/usr/bin/env python3
"""
API Mock Generator
엑셀에서 복사한 API 명세 텍스트 또는 .xlsx 파일을 파싱하여 Request/Response Mock JSON을 생성합니다.

컬럼 구조 (데이터 타입 이후 고정):
  data_type_idx + 1 = 길이(MAX)
  data_type_idx + 2 = 필수여부 (Y/N)
  data_type_idx + 3 = 구분자
  data_type_idx + 4 = 부모필드
  data_type_idx + 5 = 반복여부
  data_type_idx + 6 = 입력값(예시)
  data_type_idx + 7 = 비고

Usage:
  python3 generate_mock.py <spec_file.txt>
  python3 generate_mock.py <spec_file.xlsx> [--api API번호] [--sheet 시트명]
  cat spec.txt | python3 generate_mock.py
"""

import subprocess
import sys

# 의존성 자동 설치
def _ensure_deps():
    try:
        import openpyxl  # noqa: F401
    except ImportError:
        req = __file__.replace('scripts/generate_mock.py', 'requirements.txt')
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req, '-q'])

_ensure_deps()

import json
import re
from typing import Optional

DATA_TYPES = {'String', 'List', 'Object', 'Integer', 'int', 'Long', 'Boolean', 'Number', 'Double'}


def is_snake_case(s: str) -> bool:
    s = s.strip()
    return bool(re.match(r'^[a-z][a-zA-Z0-9_]*$', s)) and len(s) >= 2


def find_field_col(cols: list[str]) -> tuple[Optional[str], int]:
    """
    영문 필드명과 indent level(컬럼 위치 - 3) 반환.
    cols[3] = top-level (indent 0)
    cols[4] = child (indent 1)
    cols[5] = grandchild (indent 2)
    """
    for i in range(3, min(7, len(cols))):
        val = cols[i].strip()
        if is_snake_case(val) and val not in DATA_TYPES:
            return val, i - 3
    return None, 0


def find_type_col_idx(cols: list[str], field_col_idx_abs: int) -> tuple[str, int]:
    """데이터 타입과 해당 컬럼 인덱스 반환"""
    for i in range(field_col_idx_abs + 1, min(field_col_idx_abs + 8, len(cols))):
        val = cols[i].strip()
        if val in DATA_TYPES:
            return val, i
    return 'String', field_col_idx_abs + 1


def extract_example_value(raw: str) -> Optional[str]:
    """예시값 컬럼에서 첫 번째 유효한 값 추출"""
    if not raw or not raw.strip():
        return None
    lines = [ln.strip() for ln in raw.strip().splitlines() if ln.strip()]
    if not lines:
        return None
    first = lines[0]
    if first.lower() == 'null':
        return None
    # "0 : 무료" 형태 → "0"
    if re.search(r'\s*:\s*', first):
        first = re.split(r'\s*:\s*', first)[0].strip()
    return first if first else None


def default_value(field_name: str) -> str:
    """필드명 패턴 기반 기본값"""
    fn = field_name.lower()
    if any(k in fn for k in ('date', 'time', 'dt', '_at')):
        return "202603231200"
    if any(k in fn for k in ('amount', 'price', 'fee', 'cnt', 'count', 'qty')):
        return "1000"
    if any(k in fn for k in ('_cd', '_code', 'code_', 'tp_cd', 'type')):
        return "01"
    if any(k in fn for k in ('_id', '_no', '_key', '_seq', 'mpi')):
        return "12345"
    if any(k in fn for k in ('name', '_nm', 'nm_', 'title')):
        return "샘플명"
    if any(k in fn for k in ('_yn', 'flag', 'use_')):
        return "Y"
    if any(k in fn for k in ('method', 'receipt', 'purpose', 'reason')):
        return "샘플값"
    return "sample"


def is_seq_number(s: str) -> bool:
    """순번 컬럼이 숫자인지 확인 (정수 '1' 또는 실수 '1.0' 모두 허용)"""
    s = s.strip()
    try:
        return float(s) > 0
    except ValueError:
        return False


def parse_row(cols: list[str]) -> Optional[dict]:
    """단일 행 파싱 → field dict 반환, 스킵 대상은 None"""
    if len(cols) < 4:
        return None
    if not is_seq_number(cols[0]):
        return None
    section = cols[1].strip()
    if section == 'Header':
        return None

    field_name, indent = find_field_col(cols)
    if not field_name:
        return None

    field_col_abs = 3 + indent
    data_type, type_col_idx = find_type_col_idx(cols, field_col_abs)

    # 고정 오프셋 기반 컬럼 추출
    def get_col(offset: int) -> str:
        idx = type_col_idx + offset
        return cols[idx].strip() if idx < len(cols) else ''

    required_str = get_col(2)  # 필수여부
    example_raw = get_col(6)   # 입력값(예시)

    required = required_str.upper() == 'Y'
    example = extract_example_value(example_raw)

    return {
        'name': field_name,
        'type': data_type,
        'required': required,
        'example': example,
        'indent': indent
    }


def build_json(fields: list[dict], start: int = 0, parent_indent: int = -1,
               null_optional: bool = False) -> tuple[dict, int]:
    """
    재귀적으로 계층 구조 JSON 생성. (result, next_index) 반환
    null_optional=True: 필수=N 필드를 null로 채움 (리스트 2번째 항목용)
    """
    result = {}
    i = start

    while i < len(fields):
        f = fields[i]
        if f['indent'] <= parent_indent:
            break

        name = f['name']
        dtype = f['type']

        if dtype in ('List', 'Object'):
            child_start = i + 1
            child_item1, i = build_json(fields, child_start, f['indent'], null_optional=False)
            if dtype == 'List':
                child_item2, _ = build_json(fields, child_start, f['indent'], null_optional=True)
                result[name] = [child_item1, child_item2] if child_item1 else []
            else:
                result[name] = child_item1
        else:
            if f['example'] is not None:
                val = f['example']
            elif null_optional and not f['required']:
                val = None  # 리스트 2번째 항목: 선택 필드 → null
            else:
                val = default_value(name)
            result[name] = val
            i += 1

    return result, i


def parse_section(lines: list[str]) -> dict:
    fields = []
    for line in lines:
        cols = line.split('\t')
        row = parse_row(cols)
        if row:
            fields.append(row)
    body, _ = build_json(fields)
    return body


def split_sections(text: str) -> dict[str, list[str]]:
    """텍스트에서 Request/Response 섹션 분리"""
    sections = {}
    response_re = re.compile(r'응답.*인터페이스|Response', re.IGNORECASE)
    request_re = re.compile(r'요청.*인터페이스|Request', re.IGNORECASE)

    current_key = None
    current_lines = []
    counts = {'response': 0, 'request': 0}

    for line in text.splitlines():
        # 탭 없는 제목행으로 섹션 구분
        if '\t' not in line:
            if response_re.search(line):
                if current_key:
                    sections[current_key] = current_lines[:]
                counts['response'] += 1
                current_key = f"response_{counts['response']}"
                current_lines = []
                continue
            elif request_re.search(line):
                if current_key:
                    sections[current_key] = current_lines[:]
                counts['request'] += 1
                current_key = f"request_{counts['request']}"
                current_lines = []
                continue
        if current_key:
            current_lines.append(line)

    if current_key and current_lines:
        sections[current_key] = current_lines

    return sections


def generate_mocks(text: str) -> dict:
    sections = split_sections(text)
    result = {}

    for key, lines in sections.items():
        body = parse_section(lines)
        is_response = key.startswith('response')
        idx = int(key.split('_')[1])
        label = f"{'Response' if is_response else 'Request'}_{idx}"
        result[label] = body

    return result


def xlsx_to_tsv(path: str, sheet_name: str = None, api_no: str = None) -> str:
    """
    xlsx 파일을 TSV 텍스트로 변환.
    sheet_name: 특정 시트명 지정 (없으면 첫 번째 시트)
    api_no: API 번호로 해당 섹션만 필터링 (없으면 전체)
    """
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)

    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    lines = []
    in_target = api_no is None  # api_no 없으면 전체 포함

    for row in ws.iter_rows(values_only=True):
        cells = [str(c) if c is not None else '' for c in row]
        line = '\t'.join(cells).rstrip('\t')

        # API 번호 필터링: 탭 없는 제목행에서 api_no 포함 여부로 섹션 ON/OFF
        if api_no and '\t' not in line:
            in_target = api_no in line

        if in_target:
            lines.append(line)

    return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('file', nargs='?', help='spec 파일 (.txt 또는 .xlsx)')
    parser.add_argument('--api', help='API 번호 (xlsx 필터링용)')
    parser.add_argument('--sheet', help='시트명 (xlsx 전용)')
    args = parser.parse_args()

    if args.file:
        if args.file.endswith('.xlsx'):
            text = xlsx_to_tsv(args.file, sheet_name=args.sheet, api_no=args.api)
        else:
            with open(args.file, 'r', encoding='utf-8') as f:
                text = f.read()
    else:
        text = sys.stdin.read()

    mocks = generate_mocks(text)
    print(json.dumps(mocks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
