# JAL/ANA 国内線セール通知システム

JAL と ANA の国内線セール公式ページを定期監視し、重要差分があれば LINE Messaging API で通知する Python 実装です。現在は `EC2 + cron + git pull` 運用を前提にしています。

2026-07-04 時点で ANA の現行タイムセールページは `https://www.ana.co.jp/ja/jp/domestic/theme/timesale/sale/` を確認済みです。JAL はこの環境から公式サイトの自動取得が制限されており、`JAL_SALE_URL` は実ブラウザで開ける最新の公式ページに合わせて `.env` で上書きしてください。

## 構成

- `run_watch.py`: 1 回の監視を実行する CLI エントリポイント
- `scripts/cron_run.sh`: `cron` 用の実行スクリプト
- `app.py`: HTTP で実行したい場合のエントリポイント
- `watcher/`: 監視ロジック本体
- `tests/test_logic.py`: 本文抽出と通知判定の最小テスト

## 必要な環境変数

`.env.example` を元に設定します。

- `LINE_CHANNEL_ACCESS_TOKEN`
- `LINE_USER_ID`
- `JAL_SALE_URL`
- `ANA_SALE_URL`
- `STATE_DB_PATH`
- `REQUEST_TIMEOUT_SECONDS`
- `HTTP_USER_AGENT`

`.env` は `sh` で読み込むので、値に空白や括弧を入れないか、必要なら引用符で囲んでください。

## SQLite

状態保存は `SQLite` を使います。DB ファイルは `STATE_DB_PATH` に作成されます。初回実行時にテーブルを自動作成します。監視対象の識別子は内部的に以下を使います。

- `jal_domestic_sale`
- `ana_domestic_sale`

## ローカル実行

```bash
pip install -r requirements.txt
python3 run_watch.py --dry-run --json
```

`venv` を使う場合の推奨手順:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

通常実行:

```bash
./.venv/bin/python run_watch.py --json
```

HTTP で呼びたい場合:

```bash
python3 app.py
```

## EC2 セットアップ例

```bash
sudo yum install -y git python3
git clone <your-repository-url>
cd jal-ana-sale-notify
python3 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
mkdir -p data
```

`.env` を使うなら `.env.example` をコピーして実値を入れ、`cron` 側で `set -a; . ./.env; set +a` のように読み込ませます。

推奨する `.env` の例:

```sh
LINE_CHANNEL_ACCESS_TOKEN=YOUR_LINE_CHANNEL_ACCESS_TOKEN
LINE_USER_ID=YOUR_LINE_USER_ID
JAL_SALE_URL=https://www.jal.co.jp/jp/ja/dom/special/timesale/
ANA_SALE_URL=https://www.ana.co.jp/ja/jp/domestic/theme/timesale/sale/
STATE_DB_PATH=./data/watch_states.sqlite3
REQUEST_TIMEOUT_SECONDS=10
HTTP_USER_AGENT=Mozilla/5.0_(Macintosh;_Intel_Mac_OS_X_10_15_7)_AppleWebKit/537.36_(KHTML,_like_Gecko)_Chrome/137.0.0.0_Safari/537.36
```

JAL はブラウザ以外のアクセスで本文が簡略化される可能性があるため、`HTTP_USER_AGENT` はブラウザ相当の値を推奨します。`important_text` が空になった場合は `data/debug/<document_id>.html` に取得HTMLを保存します。

### 手動実行例

```bash
set -a
. ./.env
set +a
./.venv/bin/python run_watch.py --json
```

### SQLite ファイル確認例

```bash
ls -l data/watch_states.sqlite3
sqlite3 data/watch_states.sqlite3 'select document_id, last_checked_at, consecutive_error_count from watch_states;'
```

### cron 例

5 分ごとに `git pull` してから実行する例です。

```cron
*/5 * * * * cd /home/ssm-user/jal-ana-sale-notify && \
  set -a && . ./.env && set +a && \
  export GIT_PULL_BEFORE_RUN=1 && \
  /bin/bash scripts/cron_run.sh
```

`cd` のパスは、実際の配置先に合わせてください。SSM 接続なら `/home/ssm-user/jal-ana-sale-notify` になっていることがあります。

`git pull` を `cron` で回すなら、EC2 側に Git 認証が設定されている必要があります。毎回 `pip install` は不要です。依存更新が入る運用なら、デプロイ時にだけ手動で `python3 -m pip install -r requirements.txt` を実行するほうが安全です。

## 挙動

- `script`, `style`, `nav`, `footer`, `noscript`, `svg` を除去して本文抽出
- 重要行のみ抽出して hash 比較
- 3 回連続取得失敗で LINE エラー通知
- エラー通知後に正常復帰したら LINE 復旧通知
- 同一 hash は再通知しない
