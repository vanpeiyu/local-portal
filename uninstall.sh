#!/bin/bash
set -e

PLIST_NAME="com.localportal.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

# サービスを停止・削除
if [ -f "$PLIST_DEST" ]; then
    echo "サービスを停止中..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "✓ LaunchAgentを削除しました"
fi

# ログファイルを削除
if [ -f "/tmp/localportal.log" ]; then
    rm /tmp/localportal.log
    echo "✓ ログファイルを削除しました"
fi

if [ -f "/tmp/localportal.error.log" ]; then
    rm /tmp/localportal.error.log
fi

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
CERT_DIR="$PROJECT_DIR/certs"

# 証明書ディレクトリを削除
if [ -d "$CERT_DIR" ]; then
    read -p "SSL証明書を削除しますか? (y/N): " answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        rm -rf "$CERT_DIR"
        echo "✓ SSL証明書を削除しました"
    fi
fi

echo "✓ アンインストール完了"
echo ""
echo "このディレクトリ (venv含む) を削除する場合は手動で実行してください:"
echo "  rm -rf $PROJECT_DIR"
