# debt-trap

模擬決済 API（mock payment API）を提供する Django + MySQL（PyMySQL）プロジェクトです。  
Web 画面でユーザー登録 → API キー発行 → アプリから決済 API 呼び出し、という本番さながらの流れを **検証用途** で体験できます。

> 実カードへの請求は一切発生しません。検証・学習用途のみで使用してください。

---

## 1. ドキュメント

- 実装プラン: [`docs/implementation_plan.md`](docs/implementation_plan.md)
- API 仕様書（内部・実装者向け）: [`docs/api_specification.md`](docs/api_specification.md)
- API 利用ガイド（一般ユーザー向け）: [`docs/api_specification_for_users.md`](docs/api_specification_for_users.md)

---

## 2. 技術スタック

| レイヤ | 採用技術 |
| --- | --- |
| 言語 | Python 3.10+ |
| Web フレームワーク | Django 5 |
| API | Django REST Framework |
| DB | MySQL（PyMySQL を `pymysql.install_as_MySQLdb()` で接続） |
| UI | Bootstrap 5（CDN） |

---

## 3. セットアップ

### 3.1 依存パッケージ
```bash
pip install -r requirements.txt
```

### 3.2 環境変数
`.env.example` をコピーして `.env` を作成し、適宜編集してください。

```bash
cp .env.example .env
```

| 変数 | 用途 |
| --- | --- |
| `DJANGO_SECRET_KEY` | Django のシークレットキー |
| `DJANGO_DEBUG` | デバッグモード |
| `DJANGO_ALLOWED_HOSTS` | カンマ区切り |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` | MySQL 接続情報 |

### 3.3 データベースを用意する
```sql
CREATE DATABASE debt_trap CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'debt_trap'@'localhost' IDENTIFIED BY 'debt_trap';
GRANT ALL PRIVILEGES ON debt_trap.* TO 'debt_trap'@'localhost';
FLUSH PRIVILEGES;
```

### 3.4 マイグレーション
```bash
python manage.py makemigrations accounts payments
python manage.py migrate
```

### 3.5 初期管理者を作成（CLI）
Web 上の管理者は管理者ユーザーしか作れないため、最初の管理者は CLI で作成します。

```bash
python manage.py createadmin --username admin --email admin@example.com
```

または Django 標準の方法でも作成できます（自動的に admin ロールが付きます）。

```bash
python manage.py createsuperuser
```

### 3.6 開発サーバー起動
```bash
python manage.py runserver
```

ブラウザで `http://localhost:8000/` を開いてください。  
未ログインなら `/login/` に飛びます。ログイン画面の下に「新規登録はこちら」リンクがあり、そこから **一般ユーザー** を作成できます。

---

## 3.7 Docker で起動する（推奨：本番/外部公開向け）

`nginx`（リバースプロキシ・静的ファイル配信）+ `web`（gunicorn で Django）+ `db`（MySQL 8.0）の 3 コンテナ構成です。

```bash
# .env を用意（DJANGO_SECRET_KEY を必ず変更してください）
cp .env.example .env

# ビルド & 起動（マイグレーション・collectstatic は自動実行）
docker compose up -d --build
```

- アクセス: `http://localhost/`（nginx が 80 番で受け付け、`web` へプロキシ）
- 静的ファイルは `collectstatic` 後に nginx が `/static/` で配信します。

### 初期管理者を作成
```bash
docker compose exec web python manage.py createadmin --username admin --email admin@example.com
```

### デモデータ投入（任意）
```bash
docker compose exec web python manage.py seed_demo
```

### 外部から API を受け付ける場合
- `.env` の `DJANGO_ALLOWED_HOSTS` に公開ドメイン/IP を追加してください（例: `DJANGO_ALLOWED_HOSTS=api.example.com`）。
- HTTPS 化する場合は nginx で TLS を終端し（`docker/nginx/default.conf` に 443 の `server` を追加 + 証明書をマウント）、`DJANGO_CSRF_TRUSTED_ORIGINS` に `https://api.example.com` を設定してください。Django は `X-Forwarded-Proto` を見て HTTPS を認識します。

### 停止 / ログ確認
```bash
docker compose logs -f web    # アプリのログ
docker compose down           # 停止（DB データは volume に保持）
docker compose down -v        # DB データも含めて削除
```

---

## 4. デモデータ
```bash
python manage.py seed_demo
```

`demo_admin`（管理者）、`alice`、`bob`（一般）と、それぞれの取引（成功・失敗・返金）を投入します。  
パスワードはすべて `Comp1ex-Passw0rd!` です。

---

## 5. 動作確認用 cURL

```bash
# ダッシュボードで取得したキーで置き換えてください
API_KEY="pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 成功
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{ "amount": 1500, "currency": "JPY", "card_number": "4242424242424242" }'

# カード拒否
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{ "amount": 1500, "currency": "JPY", "card_number": "4000000000000000" }'
```

詳細は [`docs/api_specification_for_users.md`](docs/api_specification_for_users.md) を参照してください。

---

## 6. テスト

```bash
python manage.py test
```

`accounts` と `payments` の主要ロジック（ユーザー作成 / 権限制御 / 決済ルール / API エンドポイント）をカバーしています。

---

## 7. ディレクトリ構成

```
debt-trap/
├── manage.py
├── requirements.txt
├── .env.example
├── config/             # Django 設定 (settings, urls, wsgi, asgi)
├── accounts/           # ユーザー管理アプリ
│   └── management/commands/    # createadmin, seed_demo
├── payments/           # 決済 API & 取引履歴アプリ
│   └── api/                    # DRF (auth, permission, serializers, views)
├── templates/          # Django テンプレート (Bootstrap)
└── docs/               # ドキュメント
```

---

## 8. ライセンス・注意

検証・学習用途の **模擬** 決済 API です。本番運用を行う場合は、PCI DSS や個人情報保護関連の追加対策が必要です。
