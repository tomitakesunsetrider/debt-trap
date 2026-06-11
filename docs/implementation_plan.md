# 実装プラン（模擬決済 API: debt-trap）

本ドキュメントは、模擬的な決済 API と、それを運用するための Web 管理画面を Django + MySQL（PyMySQL）で構築するための実装プランです。

---

## 1. プロジェクト概要

### 1.1 目的
- 開発・検証用途の「模擬決済 API」を提供する。
- 本番運用さながらに、API を利用する前に Web 上でユーザー登録を行い、API キーを発行・確認できるようにする。
- 管理者ユーザーと一般（エンド）ユーザーが同一の Web サイトを使い分けて運用できるようにする。

### 1.2 想定ユースケース
- 開発者（一般ユーザー）が Web で登録 → API キーを取得 → 自分のアプリから決済 API を叩いて疎通テストを行う。
- 運用者（管理者ユーザー）が Web 上で全ユーザー・全取引を監視し、必要に応じて管理者アカウントの追加・削除を行う。

---

## 2. 技術スタック

| レイヤ | 採用技術 |
| --- | --- |
| 言語 | Python 3.x |
| Web フレームワーク | Django 5.x（標準テンプレート + Django REST Framework もしくは Django のクラスベース View） |
| API 実装 | Django REST Framework（DRF）を採用予定 |
| DB | MySQL |
| DB ドライバ | PyMySQL（`pymysql.install_as_MySQLdb()` で MySQLdb 互換として使用） |
| 認証（Web） | Django 標準の `django.contrib.auth`（セッション認証） |
| 認証（API） | 独自の API キー認証（HTTP ヘッダ `X-API-Key`） |
| 画面 | Django テンプレート + 軽量な CSS（Bootstrap 5 を想定） |

> Django REST Framework が未インストールの場合、`pip install djangorestframework` を `requirements.txt` に追記して導入する。

---

## 3. ディレクトリ構成（予定）

```
debt-trap/
├── manage.py
├── requirements.txt
├── README.md
├── docs/
│   ├── implementation_plan.md      # 本ドキュメント
│   └── api_specification.md        # API 仕様書
├── config/                         # Django プロジェクト設定
│   ├── __init__.py                 # PyMySQL を MySQLdb として登録
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── accounts/                       # ユーザー管理アプリ
│   ├── models.py                   # User モデル（AbstractUser を拡張）
│   ├── forms.py                    # ログイン / サインアップ / 管理者作成フォーム
│   ├── views.py                    # 認証・ユーザー管理ビュー
│   ├── urls.py
│   ├── admin.py
│   └── migrations/
├── payments/                       # 決済 API & 取引履歴アプリ
│   ├── models.py                   # Transaction モデル
│   ├── api/
│   │   ├── views.py                # DRF API ビュー
│   │   ├── serializers.py
│   │   ├── authentication.py       # X-API-Key 認証クラス
│   │   └── urls.py
│   ├── views.py                    # 取引履歴 Web 画面ビュー
│   ├── urls.py
│   └── migrations/
├── templates/                      # 共通テンプレート
│   ├── base.html
│   ├── accounts/
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── user_list.html
│   │   ├── admin_form.html
│   │   └── ...
│   └── payments/
│       ├── dashboard.html
│       ├── transaction_list.html
│       └── ...
└── static/                         # 静的ファイル
    └── css/
```

---

## 4. データモデル設計

### 4.1 `accounts.User`（`AbstractUser` を拡張）

| カラム | 型 | 説明 |
| --- | --- | --- |
| `id` | BigAutoField | 主キー |
| `username` | CharField(150) unique | ログイン ID |
| `email` | EmailField unique | 連絡用 |
| `password` | CharField | ハッシュ済みパスワード（Django 標準） |
| `role` | CharField(16) | `'admin'` または `'end_user'` |
| `api_key` | CharField(64) unique nullable | 一般ユーザー専用。管理者は持たない |
| `api_key_issued_at` | DateTimeField nullable | API キー発行日時 |
| `is_active` | BooleanField | アカウント有効フラグ（Django 標準） |
| `date_joined` | DateTimeField | 登録日時（Django 標準） |

#### ヘルパープロパティ
- `is_admin_role`: `role == 'admin'`
- `is_end_user_role`: `role == 'end_user'`

> Django 既存の `is_staff`/`is_superuser` ではなく、業務上のロールを `role` カラムで明確化する。Django admin サイトを使う場合に限り、`is_staff` も併用する。

### 4.2 `payments.Transaction`

| カラム | 型 | 説明 |
| --- | --- | --- |
| `id` | BigAutoField | 主キー |
| `transaction_id` | CharField(36) unique | 外部公開用 UUID |
| `user` | FK → User | API キーの所有者 |
| `kind` | CharField(16) | `'charge'`（売上） / `'refund'`（返金） |
| `amount` | DecimalField(12, 2) | 金額（最小単位ではなく主要単位、例: 1000.00） |
| `currency` | CharField(3) | ISO 4217（例: `JPY`, `USD`） |
| `card_last4` | CharField(4) | カード番号下 4 桁（テスト用に受け取った値そのまま） |
| `status` | CharField(16) | `'succeeded'` / `'failed'` |
| `error_code` | CharField(32) nullable | 失敗時のコード（例: `card_declined`） |
| `error_message` | CharField(255) nullable | 失敗時の説明 |
| `related_transaction` | FK → Transaction nullable | 返金時に元取引を指す |
| `created_at` | DateTimeField | 作成日時 |

#### インデックス
- `(user, created_at desc)`：ユーザー別履歴の高速取得
- `transaction_id`：unique
- `status`：絞り込み用

---

## 5. 決済成否のシミュレーションルール

API は本物の決済処理を行わず、リクエスト内容に応じて決定的に成否を返す。動作確認が容易になるよう、Stripe テストカードのような分かりやすい挙動を採用する。

### 5.1 カード番号末尾 4 桁による分岐
| 末尾 4 桁 | 結果 | error_code |
| --- | --- | --- |
| `0000` | 失敗 | `card_declined` |
| `0001` | 失敗 | `insufficient_funds` |
| `0002` | 失敗 | `expired_card` |
| `0119` | 失敗 | `processing_error` |
| その他 | 成功 | - |

### 5.2 金額による追加ルール
- `amount` が 0 以下 → 400 Bad Request（バリデーションエラー）
- `amount` が 1,000,000 以上 → 失敗 `amount_too_large`
- `currency` が `JPY` 以外で小数部が 2 桁を超える → 400 Bad Request

### 5.3 返金
- 元の `transaction_id` が `succeeded` でなければ失敗 `refund_not_allowed`
- 同一取引に対する複数回の `refund` は失敗 `already_refunded`

---

## 6. 画面設計（Web UI）

サイトは管理者ユーザー・一般ユーザー共通の単一の Web サイトとし、ログインユーザーのロールに応じて遷移先・表示メニューを切り替える。

### 6.1 公開ページ（未ログイン）
- `/` ：トップ。ログインしていれば `/dashboard/` にリダイレクト、未ログインなら `/login/` にリダイレクト
- `/login/`：ログイン画面
  - ページ下部に「新規登録はこちら」リンク → `/signup/`
- `/signup/`：一般ユーザー登録画面
  - ユーザー名 / メール / パスワード / パスワード（確認） を入力
  - 登録成功時に API キーを自動発行し、`/dashboard/` へ
  - **管理者ユーザーはこの画面では作成できない**

### 6.2 ダッシュボード（ログイン後）
- `/dashboard/`：ロールに応じた内容を表示
  - 一般ユーザー：
    - 自分の API キー（表示 / 再生成ボタン）
    - 自分の直近取引履歴（上位 10 件）
    - 「全取引履歴を見る」リンク → `/me/transactions/`
  - 管理者ユーザー：
    - 全ユーザー数・全取引件数・成功 / 失敗内訳のサマリ
    - 「ユーザー一覧」「全取引履歴」「管理者管理」へのリンク

### 6.3 一般ユーザー向けページ
- `/me/transactions/`：自分の取引履歴一覧（ページング、絞り込み: 日付・kind・status）
- `/me/api-key/regenerate/`：API キー再発行（POST）

### 6.4 管理者向けページ
- `/admin-portal/users/`：全ユーザー一覧（検索: ロール・有効/無効・キーワード）
- `/admin-portal/users/<id>/`：ユーザー詳細
- `/admin-portal/admins/new/`：管理者ユーザー作成
- `/admin-portal/admins/<id>/edit/`：管理者ユーザー更新
- `/admin-portal/admins/<id>/delete/`：管理者ユーザー削除（POST）
- `/admin-portal/transactions/`：全ユーザーの取引一覧（ページング、絞り込み: ユーザー・日付・kind・status）

> ルートに `/admin-portal/` を使用する理由：Django 既定の `/admin/` は `django.contrib.admin` と衝突するため。

### 6.5 権限制御
- 未ログインで管理者ページ / ダッシュボードにアクセス → `/login/` にリダイレクト
- 一般ユーザーが `/admin-portal/*` にアクセス → 403 Forbidden
- 管理者の作成・更新・削除は **管理者ユーザーのみ** が実行可能
- 一般ユーザー登録は誰でも可能（公開）

---

## 7. URL 設計（概要）

| メソッド | パス | ハンドラ | 認可 |
| --- | --- | --- | --- |
| GET | `/` | リダイレクトビュー | - |
| GET / POST | `/login/` | `LoginView` | - |
| POST | `/logout/` | `LogoutView` | ログイン |
| GET / POST | `/signup/` | `SignupView`（一般専用） | - |
| GET | `/dashboard/` | `DashboardView` | ログイン |
| GET | `/me/transactions/` | `MyTransactionListView` | 一般 |
| POST | `/me/api-key/regenerate/` | `RegenerateApiKeyView` | 一般 |
| GET | `/admin-portal/users/` | `AdminUserListView` | 管理者 |
| GET | `/admin-portal/users/<id>/` | `AdminUserDetailView` | 管理者 |
| GET / POST | `/admin-portal/admins/new/` | `AdminCreateView` | 管理者 |
| GET / POST | `/admin-portal/admins/<id>/edit/` | `AdminUpdateView` | 管理者 |
| POST | `/admin-portal/admins/<id>/delete/` | `AdminDeleteView` | 管理者 |
| GET | `/admin-portal/transactions/` | `AdminTransactionListView` | 管理者 |
| POST | `/api/v1/payments/charge` | 決済 API | API キー |
| POST | `/api/v1/payments/refund` | 返金 API | API キー |
| GET | `/api/v1/payments/<transaction_id>` | 取引取得 API | API キー |
| GET | `/api/v1/transactions` | 自分の取引一覧 API | API キー |

API の詳細は [`api_specification.md`](./api_specification.md) を参照。

---

## 8. 認証 / 認可

### 8.1 Web セッション認証
- Django 標準の `LoginView` / `LogoutView` をベースにカスタマイズ
- `LoginRequiredMixin` でログイン必須ビューを保護
- 管理者専用ビューには独自の `AdminRequiredMixin` を実装（`request.user.role == 'admin'` を判定）

### 8.2 API キー認証（DRF カスタム認証クラス）
- ヘッダ `X-API-Key: <key>` で受け取る
- `User.api_key` と一致するユーザーを `request.user` に設定
- `role == 'end_user'` かつ `is_active == True` のみ許可
- 管理者は API キーを持たないため API は利用不可

### 8.3 API キー生成方針
- `secrets.token_urlsafe(32)` で 32 バイトのランダム値を生成（約 43 文字）
- プレフィックス `pk_live_` を付けて識別性を上げる
- 例: `pk_live_aB12_x9...`

---

## 9. 設定 / インフラ

### 9.1 PyMySQL の有効化
`config/__init__.py` に下記を記載し、Django の MySQL バックエンドから PyMySQL を使えるようにする。

```python
import pymysql
pymysql.install_as_MySQLdb()
```

### 9.2 `settings.py` の主な設定
- `INSTALLED_APPS` に `rest_framework`、`accounts`、`payments` を追加
- `AUTH_USER_MODEL = 'accounts.User'`
- `DATABASES`：MySQL 接続情報（環境変数経由で読み込み）
- `LOGIN_URL = '/login/'`、`LOGIN_REDIRECT_URL = '/dashboard/'`
- `REST_FRAMEWORK` で既定の認証クラスを API キー認証に設定

### 9.3 環境変数（`.env` または OS 環境変数）
| 変数 | 用途 | 例 |
| --- | --- | --- |
| `DJANGO_SECRET_KEY` | Django のシークレットキー | ランダム文字列 |
| `DJANGO_DEBUG` | デバッグモード | `True` / `False` |
| `DB_NAME` | MySQL データベース名 | `debt_trap` |
| `DB_USER` | MySQL ユーザー | `debt_trap` |
| `DB_PASSWORD` | MySQL パスワード | - |
| `DB_HOST` | MySQL ホスト | `127.0.0.1` |
| `DB_PORT` | MySQL ポート | `3306` |

### 9.4 `requirements.txt`（最小構成イメージ）
```
Django>=5.0,<6.0
djangorestframework>=3.15
PyMySQL>=1.1
python-dotenv>=1.0
```

---

## 10. 開発フェーズ（マイルストーン）

| Phase | 内容 | 主な成果物 |
| --- | --- | --- |
| 0 | ドキュメント作成 | `docs/implementation_plan.md`, `docs/api_specification.md` |
| 1 | プロジェクト初期化 | `manage.py`, `config/`, `requirements.txt`, MySQL 接続確認 |
| 2 | ユーザー基盤 | `accounts` アプリ、`User` モデル、サインアップ / ログイン / ログアウト |
| 3 | ダッシュボード | 一般ユーザー向け API キー表示 / 再発行画面 |
| 4 | 決済 API（charge） | `payments.Transaction`、`POST /api/v1/payments/charge` |
| 5 | 決済 API（refund / get / list） | 返金・取得・一覧 API |
| 6 | 管理者ポータル | ユーザー一覧、全取引一覧、管理者 CRUD |
| 7 | UI 仕上げ・運用 | Bootstrap 適用、エラー画面、フラッシュメッセージ |
| 8 | テスト | モデル / API / ビューの基本テスト、シードデータ用の管理コマンド |

各 Phase の完了時に、ローカルで `python manage.py runserver` と `curl` で動作確認できる状態を維持する。

---

## 11. 初期データ / 管理コマンド

- `python manage.py createsuperadmin --username admin --email admin@example.com` のような独自管理コマンドを実装し、初回の管理者ユーザーを CLI から作成可能にする（Web 上の管理者は管理者ユーザーしか作れない仕様のため、初期管理者の生成手段が必要）。
- もしくは Django 標準の `createsuperuser` を `User.role = 'admin'` で作成するよう拡張する。

---

## 12. テスト方針（最小限）

- モデル：`User.api_key` の自動採番、`Transaction` の整合性（refund 制約など）
- API：成功 / 各種失敗パターン（カード末尾、金額、認証エラー）
- 権限：管理者ページに一般ユーザーがアクセスして 403、未ログインで 302、など
- 簡易な `pytest` または `python manage.py test` で実行可能にする

---

## 13. セキュリティ上の注意（割り切り）

本プロジェクトは **模擬** 決済 API のため、以下は本番品質ではない点を明示する。

- API キーは平文に近い形で DB に保存する（本番ではハッシュ化推奨）。
- HTTPS 強制やレートリミットは本ドキュメント範囲外とする。
- カード番号下 4 桁のみを受け取り、フル PAN は受け取らない（受け取っても保存しない）。
- 本番運用を想定する場合は、PCI DSS や個人情報保護関連の追加対策が必要であることを README に明記する。

---

## 14. 今後の拡張余地（参考）
- Webhook（取引ステータス変化通知）
- ダッシュボードのグラフ（取引量・成功率の時系列）
- 複数 API キー / 環境（test / live）の併用
- 監査ログ（管理者操作の履歴）

---

## 15. リファクタリングプラン

初期実装はフェーズ 1〜8（[第 10 章](#10-開発フェーズマイルストーン)）で「動くこと」を優先する。一通り機能が揃った段階で、保守性・拡張性・テスト容易性を高めるためのリファクタリングを段階的に行う。

### 15.1 リファクタリングの基本方針
- **小さく・継続的に**：機能追加とは別ブランチ／別 PR でリファクタリングを行い、1 回の変更スコープを限定する。
- **テスト先行**：手を入れる前に対象範囲の自動テストを揃え、振る舞いが変わらないことを保証する。
- **段階的移行**：互換性を壊さないよう、新旧コードを並走させ、呼び出し元を順次切り替えてから旧コードを削除する。
- **可逆性**：ドキュメント・マイグレーションを含め、ロールバック可能な単位でコミットする。

### 15.2 リファクタリング対象と優先度

| # | 対象 | 動機 | 優先度 |
| --- | --- | --- | --- |
| R1 | ビジネスロジックのサービス層分離 | View / Serializer に決済処理ロジックが混ざるのを防ぐ | 高 |
| R2 | 決済成否ルールの戦略パターン化 | カード末尾分岐・金額分岐などの判定を疎結合に | 高 |
| R3 | 権限制御の共通化（`AdminRequiredMixin` / DRF Permission） | 各ビューで `if user.role == 'admin'` が散在するのを排除 | 高 |
| R4 | エラーレスポンスの共通化（DRF Exception Handler） | エラー JSON 形式の一貫性を機械的に担保 | 高 |
| R5 | API バージョニング戦略の整理 | `/api/v1/` の運用ルールと将来の `/v2` 移行手順を明確化 | 中 |
| R6 | 設定値の集約（`django-environ` 等の導入検討） | `os.environ.get` の散在を整理 | 中 |
| R7 | テンプレートの共通化（base.html・パーシャル分割） | 画面追加時の重複を削減 | 中 |
| R8 | クエリ最適化（`select_related` / `only` / インデックス見直し） | 取引一覧の N+1・全件スキャンを抑制 | 中 |
| R9 | 型ヒント・`mypy` 導入 | 大規模化に備えた型安全性の底上げ | 中 |
| R10 | API キーのハッシュ化保管 | セキュリティ強化（本番運用想定時） | 低（条件付き高） |
| R11 | ロギング基盤の整備（構造化ログ） | 障害解析・監査の容易化 | 低 |
| R12 | フロント資産のビルドパイプライン整備 | Bootstrap CDN → ローカルビルドへ移行する場合 | 低 |

### 15.3 各テーマの詳細

#### R1. サービス層の分離
- `payments/services/` ディレクトリを新設し、`charge_payment(user, payload) -> Transaction` のような **純粋なドメイン関数** に決済処理を切り出す。
- View / Serializer はリクエスト整形と HTTP 応答のみを担当する。
- 移行手順：
  1. 既存ロジックを `services.py` に **コピー** して関数化（テスト追加）。
  2. View からはサービスを呼ぶように切り替え。
  3. View 側に残った重複ロジックを削除。

#### R2. 決済成否ルールの戦略パターン化
- `payments/rules/` に判定ルール（`CardNumberRule`, `AmountRule`, ...）を 1 クラス 1 ファイルで配置。
- 共通インターフェース例：
  ```python
  class PaymentRule(Protocol):
      def evaluate(self, request: ChargeRequest) -> RuleResult: ...
  ```
- 評価器（`RuleEngine`）がルール群を順次評価し、最初に `failed` を返したルールの結果を採用。
- 利点：
  - ルール追加が新ファイル追加のみで済む。
  - 単体テストがルール単位で書ける。
  - 将来「環境変数で確率的失敗を有効化」などの拡張がしやすい。

#### R3. 権限制御の共通化
- Web 側：
  - `accounts/mixins.py` に `AdminRequiredMixin` / `EndUserRequiredMixin` を定義し、すべての該当ビューで利用。
  - 403 用テンプレートを統一。
- API 側：
  - DRF の `BasePermission` を継承した `IsEndUser` を定義し、API ビューの `permission_classes` に設定。
  - 認証クラスとの責務分離を明確化（認証＝誰か特定する／認可＝何ができるか判定する）。

#### R4. エラーレスポンスの共通化
- DRF の `EXCEPTION_HANDLER` を上書きして、API 仕様書の共通エラー形式（`{ "error": { "code", "message", "details" } }`）を **必ず** 返すようにする。
- ドメイン例外（`PaymentRuleError`, `RefundNotAllowedError` 等）を定義し、サービス層から投げてハンドラで変換する。
- Web 側は Django のミドルウェア or `handler403/404/500` で対応。

#### R5. API バージョニング戦略
- `urls.py` を `config/urls.py` → `api/v1/urls.py` 構成に再編。
- 将来 `v2` を追加する際の指針（破壊的変更の定義／非推奨化の期間）を README に明文化。
- DRF のバージョニングクラス（`URLPathVersioning`）を採用するかを Phase R5 で決定。

#### R6. 設定値の集約
- `django-environ` または同等の薄いラッパーを導入し、`settings.py` 内の `os.environ.get` を集約。
- `.env.example` を整備し、新規参加者が即座に環境構築できる状態にする。

#### R7. テンプレート共通化
- `templates/base.html` にナビゲーション・フラッシュメッセージ表示・フッターを集約。
- 「ユーザー一覧」「取引一覧」のテーブル UI を **パーシャル**（`_table.html`）として括り出し、管理者用 / 一般用で再利用。

#### R8. クエリ最適化
- `Transaction.objects.filter(user=...).select_related('related_transaction')` の徹底。
- 一覧画面の Pagination はカーソル方式の導入も検討（巨大データ時）。
- 実行計画を `EXPLAIN` で確認し、インデックス追加・整理（複合インデックス `(user_id, created_at)` 等）。

#### R9. 型ヒント・`mypy` 導入
- `services/`・`rules/` など純粋ロジック層から型ヒントを追加。
- `mypy` を `--strict` に近づける段階的計画：
  1. `services/`・`rules/` のみ厳格チェック。
  2. ビュー・モデルへ順次拡大。

#### R10. API キーのハッシュ化保管
- 現状：平文（割り切り）。
- 改修方針：
  - DB には `api_key_hash`（SHA-256 など）と `api_key_prefix`（先頭 8 文字程度の識別子）を保存。
  - 認証時はハッシュ照合、UI にはキー再発行時のみ平文を 1 回だけ表示。
  - 既存キーの移行はバッチでハッシュ化（旧カラムを一定期間共存させる）。

#### R11. ロギング基盤
- `LOGGING` 設定で JSON 形式の構造化ログを出力できるようにする。
- リクエスト ID（X-Request-Id）をミドルウェアで採番し、Web / API ログを横断追跡可能に。

#### R12. フロント資産
- 初期は Bootstrap CDN で十分。  
- もしテーマ／ダークモード等を本格化する場合に `npm` ベースのビルドパイプライン（`django-vite` 等）導入を検討。

### 15.4 リファクタリングフェーズ（提案）

| Phase | 内容 | 前提 |
| --- | --- | --- |
| R-A | R3（権限制御の共通化）+ R4（エラー共通化） | Phase 6 完了後 |
| R-B | R1（サービス層）+ R2（ルール戦略化）+ R8（クエリ最適化） | R-A 完了後 |
| R-C | R5（バージョニング）+ R6（設定集約）+ R7（テンプレート共通化） | R-B 完了後 |
| R-D | R9（型ヒント）+ R11（ロギング） | 任意 |
| R-E | R10（API キーのハッシュ化） | 本番運用想定時に必須化 |

### 15.5 完了基準（Definition of Done）
各リファクタリング PR は、以下を満たした場合のみマージする。

- 既存テストがすべてグリーン。
- 対象範囲の単体テスト・統合テストが追加されている（または既存で十分にカバーされていることを示す）。
- API 仕様書 / 本ドキュメントに影響がある場合は同一 PR でドキュメントを更新。
- 計測可能な改善目標（例：「`/api/v1/transactions` のクエリ数が N+1 → 定数化」）が記載されている場合は、ベンチで確認済み。
