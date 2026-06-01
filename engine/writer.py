from __future__ import annotations
import gzip
import os
import shutil
from datetime import datetime


def backup(project_path: str) -> str:
    """원본을 타임스탬프 백업으로 복사하고 백업 경로를 반환한다."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    root, ext = os.path.splitext(project_path)
    backup_path = f"{root}.backup-{stamp}{ext}"
    shutil.copy2(project_path, backup_path)
    return backup_path


def apply_replacements(xml: str, replacements: dict[str, str]) -> str:
    """옛 경로 → 새 경로를 태그 경계(>...<)에 앵커해 안전하게 치환한다.
    경로 문자열이 더 긴 경로(.pek 등)의 접두일 때 오치환을 막는다."""
    out = xml
    for old, new in replacements.items():
        out = out.replace(f">{old}<", f">{new}<")
    return out


def write_prproj(xml: str, out_path: str) -> str:
    """XML을 gzip으로 압축해 .prproj로 저장한다."""
    with open(out_path, "wb") as fh:
        fh.write(gzip.compress(xml.encode("utf-8")))
    return out_path
