#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
촬영원본 폴더 -> 구글 시트 자동 동기화

NAS(예: \\\\192.168.0.45\\10tb\\촬영원본)의 폴더 구조를 훑어서
"어떤 콘텐츠의 몇 편이 실제로 촬영/입고되었는지"를 구글 시트에 자동으로 기록한다.

지원하는 폴더 구조 (둘 다 자동 인식)
  A) <root>/<콘텐츠 제목>/1편/영상파일...
  B) <root>/<콘텐츠 제목 EP.1>/영상파일...
  C) <root>/<프로그램>/<콘텐츠 제목>/2편/영상파일...   (max_depth 안이면 OK)

사용법
  python sync_footage_to_sheet.py --scan-only            # 폴더만 스캔해서 결과 출력(구글 인증 불필요)
  python sync_footage_to_sheet.py --dry-run              # 시트와 매칭까지 해보고 무엇이 바뀔지만 출력
  python sync_footage_to_sheet.py                        # 실제 시트 업데이트
  python sync_footage_to_sheet.py --loop 600             # 10분마다 반복
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

DEFAULT_CONFIG = Path(__file__).with_name("config.json")


# --------------------------------------------------------------------------
# 유틸
# --------------------------------------------------------------------------
def col_to_index(col: str) -> int:
    """'A' -> 0, 'AA' -> 26"""
    col = col.strip().upper()
    if not col or not col.isalpha():
        raise ValueError(f"잘못된 열 문자입니다: {col!r}")
    n = 0
    for ch in col:
        n = n * 26 + (ord(ch) - ord("A") + 1)
    return n - 1


def index_to_col(idx: int) -> str:
    """0 -> 'A', 26 -> 'AA'"""
    if idx < 0:
        raise ValueError(f"열 인덱스는 0 이상이어야 합니다: {idx}")
    s = ""
    idx += 1
    while idx:
        idx, rem = divmod(idx - 1, 26)
        s = chr(ord("A") + rem) + s
    return s


def human_gb(nbytes: int) -> str:
    return f"{nbytes / (1024 ** 3):.1f}"


def log(msg: str) -> None:
    print(f"[{dt.datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


# --------------------------------------------------------------------------
# 제목 정규화 / 편수 파싱
# --------------------------------------------------------------------------
# "EP.1", "EP 01", "ep1", "1편", "제2편", "3화", "_4", "-5" 등을 편수로 인식
EP_PATTERNS = [
    re.compile(r"ep[\s._-]*(\d{1,3})\b", re.IGNORECASE),
    re.compile(r"제?\s*(\d{1,3})\s*편"),
    re.compile(r"제?\s*(\d{1,3})\s*화"),
    # 끝자리 숫자 (뒤에 "(강영)" 같은 담당자 주석이 붙어도 인식)
    re.compile(r"(?:^|[\s._-])(\d{1,3})\s*(?:[（(][^)）]*[)）])?\s*$"),
]

# 정규화 시 무시할 표현 (표기 흔들림 흡수)
NOISE_PATTERNS = [
    re.compile(r"\[[^\]]*\]"),          # [흉] 같은 말머리
    re.compile(r"[（(][^)）]*[)）]"),     # (관지염) 같은 괄호 주석
    re.compile(r"\b(final|fin|최종|수정|재편집|원본|raw)\b", re.IGNORECASE),
    re.compile(r"\bv\d+\b", re.IGNORECASE),
    re.compile(r"\b\d{6,8}\b"),          # 0629, 20250629 같은 날짜 프리픽스
]

SEASON_PATTERN = re.compile(r"시즌\s*(\d+)|season\s*(\d+)|\bs(\d+)\b", re.IGNORECASE)


def _mask_seasons(name: str) -> str:
    """'시즌6'의 6을 편수로 오인하지 않도록, 길이를 유지한 채 시즌 표기를 가린다."""
    return SEASON_PATTERN.sub(lambda m: "S" * (m.end() - m.start()), name)


def strip_ep(name: str) -> tuple[str, int | None]:
    """폴더/제목 문자열에서 편수를 뽑고, 편수 표기를 제거한 나머지를 돌려준다."""
    masked = _mask_seasons(name)
    for pat in EP_PATTERNS:
        m = pat.search(masked)
        if m:
            ep = int(m.group(1))
            cleaned = (name[: m.start()] + " " + name[m.end():]).strip()
            return cleaned, ep
    return name, None


def normalize(text: str, aliases: dict[str, str] | None = None) -> str:
    """비교용 키. 공백/기호/말머리/날짜를 걷어내고 시즌 표기를 통일한다."""
    s = unicodedata.normalize("NFKC", text or "")
    if aliases:
        for wrong, right in aliases.items():
            s = s.replace(wrong, right)
    for pat in NOISE_PATTERNS:
        s = pat.sub(" ", s)
    s = SEASON_PATTERN.sub(lambda m: "s" + next(g for g in m.groups() if g), s)
    s = re.sub(r"[^0-9a-zA-Z가-힣]+", "", s)
    return s.lower()


def similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        # 짧은 쪽이 긴 쪽에 통째로 들어가면 강한 신호로 본다
        return max(0.9, SequenceMatcher(None, a, b).ratio())
    return SequenceMatcher(None, a, b).ratio()


# --------------------------------------------------------------------------
# 폴더 스캔
# --------------------------------------------------------------------------
@dataclass
class FootageUnit:
    """실제 원본 파일이 들어있는 '한 편' 단위."""
    rel_path: str
    abs_path: str
    title_raw: str
    ep: int | None
    clip_count: int = 0
    total_bytes: int = 0
    latest_mtime: float = 0.0
    key: str = ""          # 경로 전체(프로그램 폴더 포함) 기준 비교키
    alt_key: str = ""      # 가장 안쪽 제목 폴더만으로 만든 비교키

    @property
    def latest_date(self) -> str:
        if not self.latest_mtime:
            return ""
        return dt.datetime.fromtimestamp(self.latest_mtime).strftime("%Y-%m-%d")


def _folder_stats(folder: Path, exts: set[str], min_bytes: int) -> tuple[int, int, float]:
    """해당 폴더(하위 포함)의 영상 파일 개수/총용량/최신 수정시각."""
    count = 0
    total = 0
    latest = 0.0
    for dirpath, _dirnames, filenames in os.walk(folder):
        for fn in filenames:
            if exts and Path(fn).suffix.lower() not in exts:
                continue
            fp = Path(dirpath) / fn
            try:
                st = fp.stat()
            except OSError:
                continue
            if st.st_size < min_bytes:
                continue
            count += 1
            total += st.st_size
            latest = max(latest, st.st_mtime)
    return count, total, latest


def _has_subfolder(folder: Path, ignore: set[str]) -> bool:
    try:
        return any(p.is_dir() and p.name.lower() not in ignore and not p.name.startswith(".")
                   for p in folder.iterdir())
    except OSError:
        return False


def scan_root(cfg: dict[str, Any]) -> list[FootageUnit]:
    scan_cfg = cfg.get("scan", {})
    root = Path(cfg["root_path"])
    if not root.exists():
        raise SystemExit(
            f"촬영원본 경로에 접근할 수 없습니다: {root}\n"
            f"  - 네트워크 드라이브가 연결되어 있는지 확인하세요.\n"
            f'  - 인증이 필요하면 먼저 실행: net use \\\\192.168.0.45\\10tb /user:<아이디> <비밀번호>'
        )

    exts = {e.lower() if e.startswith(".") else "." + e.lower()
            for e in scan_cfg.get("video_extensions", [])}
    min_bytes = int(scan_cfg.get("min_file_size_mb", 0)) * 1024 * 1024
    max_depth = int(scan_cfg.get("max_depth", 3))
    ignore = {name.lower() for name in scan_cfg.get("ignore_folders", [])}
    aliases = cfg.get("matching", {}).get("aliases", {})

    units: list[FootageUnit] = []

    def walk(folder: Path, depth: int, parts: list[str]) -> None:
        try:
            children = [p for p in folder.iterdir() if p.is_dir()]
        except OSError as exc:
            log(f"  ! 폴더를 읽지 못했습니다: {folder} ({exc})")
            children = []
        children = [c for c in children if c.name.lower() not in ignore
                    and not c.name.startswith(".")]

        for child in children:
            child_parts = parts + [child.name]
            count, total, latest = _folder_stats(child, exts, min_bytes)
            deeper = depth + 1 < max_depth and _has_subfolder(child, ignore)

            # 이 폴더 밑에 영상이 있고, 더 파고들 하위 폴더가 없으면 = 한 편
            if count and not deeper:
                units.append(_make_unit(root, child, child_parts, count, total, latest, aliases))
            elif deeper:
                before = len(units)
                walk(child, depth + 1, child_parts)
                # 하위에서 아무 편도 못 찾았는데 영상은 있다면, 이 폴더 자체를 한 편으로 본다
                if len(units) == before and count:
                    units.append(_make_unit(root, child, child_parts, count, total, latest, aliases))

    walk(root, 0, [])
    return units


def _make_unit(root: Path, folder: Path, parts: list[str], count: int,
               total: int, latest: float, aliases: dict[str, str]) -> FootageUnit:
    """경로 조각들에서 제목과 편수를 뽑아 FootageUnit을 만든다.

    편수는 가장 안쪽 폴더명부터 거슬러 올라가며 찾는다.
    ('시즌6 해장엽/2편' -> 제목 '시즌6 해장엽', 편수 2)
    """
    ep: int | None = None
    title_parts: list[str] = []
    for name in reversed(parts):
        if ep is None:
            cleaned, found = strip_ep(name)
            if found is not None:
                ep = found
                if cleaned.strip():
                    title_parts.insert(0, cleaned.strip())
                continue
        title_parts.insert(0, name)

    title_raw = " ".join(title_parts).strip() or folder.name
    leaf_title = title_parts[-1] if title_parts else folder.name
    return FootageUnit(
        rel_path="/".join(parts),
        abs_path=str(folder),
        title_raw=title_raw,
        ep=ep,
        clip_count=count,
        total_bytes=total,
        latest_mtime=latest,
        key=normalize(title_raw, aliases),
        alt_key=normalize(leaf_title, aliases),
    )


# --------------------------------------------------------------------------
# 시트 행
# --------------------------------------------------------------------------
@dataclass
class SheetRow:
    row_no: int              # 1-based 실제 시트 행 번호
    values: list[str]
    program: str = ""
    title: str = ""
    ep: int | None = None
    key: str = ""
    matched: list[FootageUnit] = field(default_factory=list)


# --------------------------------------------------------------------------
# 매칭
# --------------------------------------------------------------------------
def match_units_to_rows(units: list[FootageUnit], rows: list[SheetRow],
                        min_score: float) -> list[FootageUnit]:
    """각 원본 폴더를 가장 잘 맞는 시트 행에 붙인다. 매칭 실패한 폴더 목록을 반환."""
    unmatched: list[FootageUnit] = []
    for unit in units:
        best: SheetRow | None = None
        best_score = 0.0
        for row in rows:
            if not row.key:
                continue
            # 편수가 양쪽 다 있으면 반드시 같아야 한다 (편수 오인이 제일 위험)
            if unit.ep is not None and row.ep is not None and unit.ep != row.ep:
                continue
            if (unit.ep is None) != (row.ep is None):
                penalty = 0.05
            else:
                penalty = 0.0
            score = max(similarity(unit.key, row.key),
                        similarity(unit.alt_key, row.key)) - penalty
            if score > best_score:
                best_score, best = score, row
        if best is not None and best_score >= min_score:
            best.matched.append(unit)
        else:
            unmatched.append(unit)
    return unmatched


# --------------------------------------------------------------------------
# 구글 시트
# --------------------------------------------------------------------------
def build_service(cfg: dict[str, Any]):
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        raise SystemExit(
            "구글 라이브러리가 없습니다. 먼저 설치하세요:\n"
            "  pip install -r requirements.txt"
        )
    g = cfg["google"]
    key_path = Path(g["service_account_file"])
    if not key_path.is_absolute():
        key_path = Path(__file__).with_name(str(key_path))
    if not key_path.exists():
        raise SystemExit(f"서비스 계정 키 파일이 없습니다: {key_path}")
    creds = Credentials.from_service_account_file(
        str(key_path), scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_rows(service, cfg: dict[str, Any]) -> list[SheetRow]:
    g = cfg["google"]
    cols = g["columns"]
    aliases = cfg.get("matching", {}).get("aliases", {})
    header_row = int(g.get("header_row", 1))
    last_col = index_to_col(max(col_to_index(c) for c in cols.values()))
    rng = f"'{g['sheet_name']}'!A1:{last_col}"

    resp = service.spreadsheets().values().get(
        spreadsheetId=g["spreadsheet_id"], range=rng
    ).execute()
    raw = resp.get("values", [])

    title_idx = col_to_index(cols["title"])
    program_idx = col_to_index(cols["program"]) if "program" in cols else None

    rows: list[SheetRow] = []
    current_program = ""
    for i, values in enumerate(raw, start=1):
        if i <= header_row:
            continue
        padded = list(values) + [""] * (col_to_index(last_col) + 1 - len(values))
        title = (padded[title_idx] or "").strip()
        if program_idx is not None and (padded[program_idx] or "").strip():
            # A열은 병합된 카테고리라 값이 첫 행에만 있다 -> 아래로 이어서 채운다
            current_program = padded[program_idx].strip()
        if not title:
            continue
        base, ep = strip_ep(title)
        rows.append(SheetRow(
            row_no=i,
            values=padded,
            program=current_program,
            title=title,
            ep=ep,
            key=normalize(base, aliases),
        ))
    return rows


def build_updates(rows: list[SheetRow], cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """변경이 필요한 셀만 골라 batchUpdate 데이터를 만든다."""
    g = cfg["google"]
    cols = g["columns"]
    labels = cfg.get("status_labels", {})
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    sheet = g["sheet_name"]

    writable = {k: cols[k] for k in
                ("status", "clip_count", "size_gb", "shot_date", "folder_path", "checked_at")
                if k in cols}
    updates: list[dict[str, Any]] = []

    for row in rows:
        if row.matched:
            clips = sum(u.clip_count for u in row.matched)
            size = sum(u.total_bytes for u in row.matched)
            latest = max((u.latest_mtime for u in row.matched), default=0.0)
            paths = " | ".join(sorted({u.rel_path for u in row.matched}))
            eps = sorted({u.ep for u in row.matched if u.ep is not None})
            status = labels.get("found", "원본확인")
            if len(row.matched) > 1 and eps:
                status = f"{status} ({', '.join(f'{e}편' for e in eps)})"
            new = {
                "status": status,
                "clip_count": str(clips),
                "size_gb": human_gb(size),
                "shot_date": dt.datetime.fromtimestamp(latest).strftime("%Y-%m-%d") if latest else "",
                "folder_path": paths,
            }
        else:
            if not cfg.get("mark_missing", True):
                continue
            new = {
                "status": labels.get("missing", "원본없음"),
                "clip_count": "",
                "size_gb": "",
                "shot_date": "",
                "folder_path": "",
            }

        # 값이 실제로 달라진 행만 쓴다 (불필요한 API 쓰기/기록 방지)
        row_updates: list[dict[str, Any]] = []
        changed = False
        for field_name, col in writable.items():
            if field_name == "checked_at":
                continue
            idx = col_to_index(col)
            old = (row.values[idx] if idx < len(row.values) else "") or ""
            value = new.get(field_name, "")
            if old.strip() != value:
                changed = True
            row_updates.append({
                "range": f"'{sheet}'!{col}{row.row_no}",
                "values": [[value]],
            })

        if not changed:
            continue

        if "checked_at" in writable:
            row_updates.append({
                "range": f"'{sheet}'!{writable['checked_at']}{row.row_no}",
                "values": [[now]],
            })
        updates.extend(row_updates)
    return updates


def ensure_sheet(service, spreadsheet_id: str, title: str) -> None:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    names = {s["properties"]["title"] for s in meta.get("sheets", [])}
    if title in names:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": title}}}]},
    ).execute()
    log(f"시트 탭 생성: {title}")


def write_unmatched(service, cfg: dict[str, Any], unmatched: list[FootageUnit]) -> None:
    g = cfg["google"]
    tab = g.get("unmatched_sheet")
    if not tab:
        return
    ensure_sheet(service, g["spreadsheet_id"], tab)
    header = ["폴더 경로", "추정 제목", "추정 편수", "파일 수", "용량(GB)", "최종 수정일", "확인 시각"]
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    body = [header] + [
        [u.rel_path, u.title_raw, str(u.ep or ""), str(u.clip_count),
         human_gb(u.total_bytes), u.latest_date, now]
        for u in sorted(unmatched, key=lambda x: x.rel_path)
    ]
    service.spreadsheets().values().clear(
        spreadsheetId=g["spreadsheet_id"], range=f"'{tab}'!A:Z", body={}
    ).execute()
    service.spreadsheets().values().update(
        spreadsheetId=g["spreadsheet_id"],
        range=f"'{tab}'!A1",
        valueInputOption="RAW",
        body={"values": body},
    ).execute()


def write_headers(service, cfg: dict[str, Any]) -> None:
    """상태 열 머리글이 비어 있으면 채워 넣는다."""
    g = cfg["google"]
    cols = g["columns"]
    header_row = int(g.get("header_row", 1))
    titles = {
        "status": "원본상태",
        "clip_count": "파일수",
        "size_gb": "용량(GB)",
        "shot_date": "촬영일(파일기준)",
        "folder_path": "원본폴더",
        "checked_at": "확인시각",
    }
    data = [
        {"range": f"'{g['sheet_name']}'!{cols[k]}{header_row}", "values": [[v]]}
        for k, v in titles.items() if k in cols
    ]
    if data:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=g["spreadsheet_id"],
            body={"valueInputOption": "RAW", "data": data},
        ).execute()
        log("상태 열 머리글을 기록했습니다.")


# --------------------------------------------------------------------------
# 실행
# --------------------------------------------------------------------------
def print_scan(units: list[FootageUnit]) -> None:
    if not units:
        log("영상 파일이 들어있는 폴더를 찾지 못했습니다. config.json의 video_extensions / min_file_size_mb를 확인하세요.")
        return
    log(f"원본 폴더 {len(units)}개를 찾았습니다.")
    width = max(len(u.rel_path) for u in units)
    for u in sorted(units, key=lambda x: x.rel_path):
        ep = f"{u.ep}편" if u.ep is not None else "편수?"
        print(f"  {u.rel_path.ljust(width)}  | {ep:>5} | {u.clip_count:>3}개 | "
              f"{human_gb(u.total_bytes):>7}GB | {u.latest_date}")


def run_once(cfg: dict[str, Any], scan_only: bool, dry_run: bool, init_headers: bool) -> None:
    log(f"스캔 시작: {cfg['root_path']}")
    units = scan_root(cfg)
    log(f"원본 폴더 {len(units)}개 발견")

    if scan_only:
        print_scan(units)
        return

    service = build_service(cfg)
    if init_headers and not dry_run:
        write_headers(service, cfg)

    rows = read_rows(service, cfg)
    log(f"시트에서 콘텐츠 행 {len(rows)}개를 읽었습니다.")

    min_score = float(cfg.get("matching", {}).get("min_score", 0.72))
    unmatched = match_units_to_rows(units, rows, min_score)
    matched_rows = [r for r in rows if r.matched]
    log(f"매칭 성공: 시트 {len(matched_rows)}행 / 폴더 {len(units) - len(unmatched)}개, "
        f"매칭 실패 폴더 {len(unmatched)}개")

    updates = build_updates(rows, cfg)
    if dry_run:
        for r in matched_rows:
            eps = ", ".join(f"{u.ep}편" if u.ep is not None else "?" for u in r.matched)
            print(f"  [{r.row_no:>4}] {r.title}  <-  {eps}  ({sum(u.clip_count for u in r.matched)}개 파일)")
        for u in unmatched:
            print(f"  [미매칭] {u.rel_path}")
        log(f"(dry-run) 변경 예정 셀 {len(updates)}개 — 실제로는 쓰지 않았습니다.")
        return

    if updates:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=cfg["google"]["spreadsheet_id"],
            body={"valueInputOption": "RAW", "data": updates},
        ).execute()
        log(f"시트 업데이트 완료: 셀 {len(updates)}개")
    else:
        log("변경된 내용이 없습니다.")

    write_unmatched(service, cfg, unmatched)
    log("동기화 완료")


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(
            f"설정 파일이 없습니다: {path}\n"
            f"  config.example.json 을 config.json 으로 복사한 뒤 값을 채우세요."
        )
    with path.open(encoding="utf-8") as f:
        cfg = json.load(f)
    for required in ("root_path", "google"):
        if required not in cfg:
            raise SystemExit(f"설정에 '{required}' 항목이 필요합니다: {path}")
    return cfg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="촬영원본 폴더를 구글 시트에 자동 반영합니다.")
    ap.add_argument("-c", "--config", type=Path, default=DEFAULT_CONFIG, help="설정 파일 경로")
    ap.add_argument("--scan-only", action="store_true", help="폴더 스캔 결과만 출력 (구글 인증 없음)")
    ap.add_argument("--dry-run", action="store_true", help="매칭 결과만 보고 시트는 건드리지 않음")
    ap.add_argument("--init-headers", action="store_true", help="상태 열 머리글을 시트에 써넣음")
    ap.add_argument("--loop", type=int, metavar="초", help="지정한 간격으로 계속 반복 실행")
    args = ap.parse_args(argv)

    cfg = load_config(args.config)

    while True:
        try:
            run_once(cfg, args.scan_only, args.dry_run, args.init_headers)
        except SystemExit:
            raise
        except Exception as exc:  # 루프 모드에서 일시적 오류로 죽지 않게
            log(f"오류: {exc.__class__.__name__}: {exc}")
            if not args.loop:
                return 1
        if not args.loop:
            return 0
        time.sleep(args.loop)


if __name__ == "__main__":
    sys.exit(main())
