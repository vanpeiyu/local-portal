#!/bin/bash

PLIST_DEST="$HOME/Library/LaunchAgents/com.localportal.plist"

if [ -f "$PLIST_DEST" ]; then
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
    rm "$PLIST_DEST"
    echo "✓ Local Portalを削除しました"
else
    echo "サービスは登録されていません"
fi
