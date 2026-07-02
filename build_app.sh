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

    # --- 배포용 zip 패키징 (앱 + 설명서 함께) ---
    echo ""
    echo "📦 배포용 zip 생성 중..."
    STAGE="dist/release/Premiere Relink"
    rm -rf "dist/release"
    mkdir -p "$STAGE"
    ditto "dist/Premiere Relink.app" "$STAGE/Premiere Relink.app"
    cp dist-assets/*.txt "$STAGE/"
    rm -f "dist/Premiere Relink.zip"
    # ditto = Finder와 동일한 압축 엔진 (리소스 포크/확장속성 보존)
    ditto -c -k --sequesterRsrc --keepParent "$STAGE" "dist/Premiere Relink.zip"
    rm -rf "dist/release"
    echo "   → dist/Premiere Relink.zip (배포용)"

    echo ""
    echo "Applications 폴더로 복사하려면:"
    echo "   cp -r 'dist/Premiere Relink.app' /Applications/"
    open dist/
else
    echo "❌ 빌드 실패"
    exit 1
fi
