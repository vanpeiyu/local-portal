# Local Portal

ローカルで動いているサーバーを一覧表示するダッシュボード

## デーモンとして起動（推奨）

```bash
chmod +x install.sh
./install.sh
```

Mac起動時に自動で立ち上がります。http://localhost:8888 をブックマーク。

### 管理コマンド

```bash
# 停止
launchctl unload ~/Library/LaunchAgents/com.localportal.plist

# 起動
launchctl load ~/Library/LaunchAgents/com.localportal.plist

# ログ確認
tail -f /tmp/localportal.log

# アンインストール
./uninstall.sh
```

## 手動起動

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8888
```

## 機能

- ポート3000-9999をスキャンして開いているポートを検出
- プロセス名を表示
- ワンクリックで各サーバーにアクセス
