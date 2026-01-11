# Local Portal

ローカルで動いているサーバーを一覧表示するダッシュボード

## 概要

Local Portalは、ローカル環境で起動中のWebサーバーを自動検出し、ダッシュボード形式で一覧表示するツールです。

### 主な機能

- ポート3000-9999をスキャンして開いているポートを自動検出
- プロセス名とページタイトルを表示
- サーバーのサムネイル画像を自動取得
- ワンクリックで各サーバーにアクセス
- ダーク/ライトモード切替
- HTTPSリバースプロキシ（サブドメインベース）

## 対応環境

- macOS 10.15 (Catalina) 以降
- Python 3.8 以降

## 前提条件

以下がシステムにインストールされている必要があります：

- Python 3.8+
- pip
- `lsof` コマンド（macOSに標準搭載）
- mkcert（SSL証明書生成用）

```bash
brew install mkcert
mkcert -install
```

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

Mac起動時に自動で立ち上がります。https://[ホスト名]:8888 をブックマーク。

## HTTPSリバースプロキシ

サブドメインを使って、ローカルサーバーにHTTPSでアクセスできます。

### 仕組み

`localhost:5173` で動いているサーバーに `https://5173.air.local:8888` でアクセス可能（`air` はホスト名の例）。

- WebSocket対応（Vite等のHMRが動作）
- mkcertによる証明書で警告なし

### DNS設定（初回のみ）

dnsmasqでワイルドカードDNSを設定します：

```bash
brew install dnsmasq
echo 'address=/.local/127.0.0.1' >> $(brew --prefix)/etc/dnsmasq.conf
sudo brew services restart dnsmasq
sudo mkdir -p /etc/resolver
echo 'nameserver 127.0.0.1' | sudo tee /etc/resolver/local
```

### 使用例

| ローカルサーバー | HTTPSアクセス |
|-----------------|---------------|
| localhost:3000  | https://3000.air.local:8888 |
| localhost:5173  | https://5173.air.local:8888 |
| localhost:8080  | https://8080.air.local:8888 |

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
- SSL証明書（確認あり）

プロジェクトディレクトリ自体は手動で削除してください。

## 手動起動

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --port 8888
```

## トラブルシューティング

### サービスが起動しない

```bash
# ログを確認
tail -f /tmp/localportal.log
tail -f /tmp/localportal.error.log
```

### ポート8888が既に使用されている

`main.py` の起動ポートを変更してください：

```python
# main.py の最終行付近
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8888)  # ← ポート番号を変更
```

または、手動起動時にポートを指定：

```bash
uvicorn main:app --port 8889
```

### Playwrightのインストールに失敗する

手動でインストールを試してください：

```bash
source venv/bin/activate
pip install playwright
playwright install chromium
```

### サムネイルが表示されない

- Chromiumが正しくインストールされているか確認
- 対象サーバーが正常に応答しているか確認
- ネットワーク設定でlocalhostへのアクセスがブロックされていないか確認

### 権限エラーが発生する

```bash
# スクリプトに実行権限を付与
chmod +x install.sh
chmod +x uninstall.sh
```

## セキュリティに関する注意

- このツールは **ローカル環境専用** です
- 外部ネットワークからのアクセスは想定していません
- 本番環境での使用は推奨しません

## ライセンス

MIT License
