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
