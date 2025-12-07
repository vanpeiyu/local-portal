# Local Portal

ローカルで動いているサーバーを一覧表示するダッシュボード

## インストール

```bash
chmod +x install.sh
./install.sh
```

以下が自動で実行されます：
- Python仮想環境の作成
- 依存パッケージのインストール
- Playwrightブラウザ（Chromium）のインストール
- LaunchAgentへの登録と起動

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
chmod +x uninstall.sh
./uninstall.sh
```

アンインストールスクリプトは以下を削除します：
- LaunchAgentの登録
- ログファイル (/tmp/localportal.log, /tmp/localportal.error.log)

プロジェクトディレクトリ自体は手動で削除してください。

## 手動起動

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8888
```

## 機能

- ポート3000-9999をスキャンして開いているポートを検出
- プロセス名とページタイトルを表示
- サーバーのサムネイル画像を自動取得
- ワンクリックで各サーバーにアクセス
- ダーク/ライトモード切替
