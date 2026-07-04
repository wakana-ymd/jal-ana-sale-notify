# JAL/ANA 国内線セール通知システム

JAL と ANA の国内線セール公式ページを定期監視し、重要差分があれば LINE Messaging API で通知する Python 実装です。現在は `EC2 + cron + git pull` 運用を前提にしています。

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

## SQLite

状態保存は `SQLite` を使います。DB ファイルは `STATE_DB_PATH` に作成されます。初回実行時にテーブルを自動作成します。監視対象の識別子は内部的に以下を使います。

- `jal_domestic_sale`
- `ana_domestic_sale`

## ローカル実行

```bash
pip install -r requirements.txt
python3 run_watch.py --dry-run --json
```

通常実行:

```bash
python3 run_watch.py --json
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
python3 -m pip install -r requirements.txt
mkdir -p data
```

`.env` を使うなら `.env.example` をコピーして実値を入れ、`cron` 側で `set -a; . ./.env; set +a` のように読み込ませます。

### 手動実行例

```bash
set -a
. ./.env
set +a
python3 run_watch.py --json
```

### SQLite ファイル確認例

```bash
ls -l data/watch_states.sqlite3
sqlite3 data/watch_states.sqlite3 'select document_id, last_checked_at, consecutive_error_count from watch_states;'
```

### cron 例

5 分ごとに `git pull` してから実行する例です。

```cron
*/5 * * * * cd /home/ec2-user/jal-ana-sale-notify && \
  set -a && . ./.env && set +a && \
  export GIT_PULL_BEFORE_RUN=1 && \
  /bin/bash scripts/cron_run.sh
```

`git pull` を `cron` で回すなら、EC2 側に Git 認証が設定されている必要があります。毎回 `pip install` は不要です。依存更新が入る運用なら、デプロイ時にだけ手動で `python3 -m pip install -r requirements.txt` を実行するほうが安全です。

## 挙動

- `script`, `style`, `nav`, `footer`, `noscript`, `svg` を除去して本文抽出
- 重要行のみ抽出して hash 比較
- 3 回連続取得失敗で LINE エラー通知
- エラー通知後に正常復帰したら LINE 復旧通知
- 同一 hash は再通知しない
