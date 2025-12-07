#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
PLIST_NAME="com.localportal.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

# 仮想環境を作成
if [ ! -d "$VENV_DIR" ]; then
    echo "仮想環境を作成中..."
    python3 -m venv "$VENV_DIR"
fi

# 依存関係をインストール
echo "依存関係をインストール中..."
"$VENV_DIR/bin/pip" install -q -r "$PROJECT_DIR/requirements.txt"

UVICORN_PATH="$VENV_DIR/bin/uvicorn"

# plistファイルを生成
cat > /tmp/com.localportal.plist.tmp << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.localportal</string>
    <key>ProgramArguments</key>
    <array>
        <string>$UVICORN_PATH</string>
        <string>main:app</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8888</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/localportal.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/localportal.error.log</string>
</dict>
</plist>
EOF

# LaunchAgentsディレクトリを作成
mkdir -p "$HOME/Library/LaunchAgents"

# plistファイルをコピー
cp /tmp/com.localportal.plist.tmp "$PLIST_DEST"
rm /tmp/com.localportal.plist.tmp

# サービスを登録・起動
launchctl unload "$PLIST_DEST" 2>/dev/null || true
launchctl load "$PLIST_DEST"

echo "✓ Local Portalをデーモンとして登録しました"
echo "✓ http://localhost:8888 でアクセスできます"
echo ""
echo "コマンド:"
echo "  停止: launchctl unload $PLIST_DEST"
echo "  起動: launchctl load $PLIST_DEST"
echo "  ログ: tail -f /tmp/localportal.log"
