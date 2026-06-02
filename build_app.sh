#!/bin/bash
# Premiere Relink.app 빌드 스크립트
set -e

cd "$(dirname "$0")"

echo "🔨 빌드 시작..."
python3 -m PyInstaller PremiereRelink.spec --clean --noconfirm

if [ -d "dist/Premiere Relink.app" ]; then
    echo ""
    echo "✅ 빌드 완료!"
    echo "   → dist/Premiere Relink.app"
    echo ""
    echo "Applications 폴더로 복사하려면:"
    echo "   cp -r 'dist/Premiere Relink.app' /Applications/"
    open dist/
else
    echo "❌ 빌드 실패"
    exit 1
fi
