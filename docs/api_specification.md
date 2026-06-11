# API 仕様書（模擬決済 API: debt-trap）

本ドキュメントは、`debt-trap` プロジェクトが提供する模擬決済 API のリクエスト / レスポンス仕様を定義します。

実装方針・画面仕様などは [`implementation_plan.md`](./implementation_plan.md) を参照してください。

---

## 1. 基本情報

| 項目 | 値 |
| --- | --- |
| ベース URL（開発） | `http://localhost:8000` |
| API バージョン | `v1` |
| API ルートパス | `/api/v1` |
| データフォーマット | JSON（リクエスト / レスポンスとも `application/json`） |
| 文字コード | UTF-8 |
| 日付フォーマット | ISO 8601（例: `2026-06-11T02:41:00Z`） |
| 通貨 | ISO 4217 3 文字コード（例: `JPY`, `USD`） |

---

## 2. 認証

すべての API は HTTP ヘッダによる API キー認証を必要とします。

### 2.1 ヘッダ
```
X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

### 2.2 認証ルール
- API キーは **一般（エンド）ユーザー** のみが保有する。
- 管理者ユーザーは API キーを持たず、API を呼び出すことはできない。
- API キーが欠落・不正・無効化されている場合、`401 Unauthorized` を返す。
- ユーザーが `is_active = False`（無効化）の場合も `401 Unauthorized` を返す。

### 2.3 認証エラー時のレスポンス例

```http
HTTP/1.1 401 Unauthorized
Content-Type: application/json

{
  "error": {
    "code": "unauthorized",
    "message": "Invalid or missing API key."
  }
}
```

---

## 3. 共通仕様

### 3.1 共通レスポンスフォーマット

#### 成功レスポンス
- HTTP ステータス `2xx`
- ボディはリソースに対応する JSON オブジェクト

#### エラーレスポンス
- HTTP ステータス `4xx` / `5xx`
- 共通ボディ：

```json
{
  "error": {
    "code": "<machine_readable_code>",
    "message": "<human readable message>",
    "details": { "field": ["..."] }
  }
}
```

`details` はバリデーションエラーなど、フィールド単位の情報を返す場合のみ含まれる。

### 3.2 共通 HTTP ステータス
| ステータス | 意味 |
| --- | --- |
| `200 OK` | 取得・参照成功 |
| `201 Created` | 取引等の作成成功 |
| `400 Bad Request` | リクエスト形式 / バリデーションエラー |
| `401 Unauthorized` | 認証エラー（API キー不正） |
| `403 Forbidden` | 認可エラー（権限不足） |
| `404 Not Found` | リソースが存在しない |
| `409 Conflict` | 競合（例: 二重返金） |
| `422 Unprocessable Entity` | ビジネスルール違反（例: 残高不足のシミュレーション） |
| `500 Internal Server Error` | サーバーエラー |

> 模擬決済におけるカード拒否（card_declined など）は、HTTP は `200 OK` を返し、レスポンスボディの `status` フィールドを `failed` にする。HTTP レベルのエラーとビジネスレベルの「決済失敗」を明確に分ける。

### 3.3 通貨と金額
- `amount` は数値（整数または小数）。
- `JPY` の場合は **整数値のみ** 受け付ける（小数指定で `400` を返す）。
- `USD` 等は小数 2 桁まで受け付ける。
- 0 以下の金額は `400`。
- `1,000,000` 以上の金額はビジネスルールにより `failed` ＋ `amount_too_large`。

### 3.4 取引 ID
- `transaction_id`：サーバー側で発行する UUIDv4 文字列（例: `7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e`）。
- API レスポンスでは常にこの値で取引を特定する。

---

## 4. エンドポイント一覧

| メソッド | パス | 概要 |
| --- | --- | --- |
| POST | `/api/v1/payments/charge` | 売上（決済）リクエスト |
| POST | `/api/v1/payments/refund` | 返金リクエスト |
| GET | `/api/v1/payments/{transaction_id}` | 取引情報の取得 |
| GET | `/api/v1/transactions` | 自分の取引一覧 |

---

## 5. エンドポイント詳細

### 5.1 `POST /api/v1/payments/charge`

決済（売上）リクエストを行う。

#### リクエストヘッダ
```
X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

#### リクエストボディ
| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `amount` | number | ○ | 金額。`currency = JPY` の場合は整数のみ。 |
| `currency` | string(3) | ○ | ISO 4217 通貨コード（例: `JPY`, `USD`）。 |
| `card_number` | string | ○ | カード番号（テスト用）。下 4 桁のみ参照・保存。 |
| `card_holder` | string | × | カードホルダー名。 |
| `card_exp_month` | integer | × | 有効期限月（1〜12）。 |
| `card_exp_year` | integer | × | 有効期限年（YYYY）。 |
| `card_cvc` | string | × | CVC（保存しない）。 |
| `description` | string | × | 任意のメモ。 |

#### リクエスト例
```http
POST /api/v1/payments/charge HTTP/1.1
Host: localhost:8000
X-API-Key: pk_live_abc123...
Content-Type: application/json

{
  "amount": 1500,
  "currency": "JPY",
  "card_number": "4242424242424242",
  "card_holder": "TARO YAMADA",
  "card_exp_month": 12,
  "card_exp_year": 2030,
  "card_cvc": "123",
  "description": "Order #1234"
}
```

#### 成功レスポンス（`201 Created`）
```json
{
  "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
  "kind": "charge",
  "status": "succeeded",
  "amount": 1500,
  "currency": "JPY",
  "card_last4": "4242",
  "description": "Order #1234",
  "created_at": "2026-06-11T02:41:00Z"
}
```

#### 決済失敗レスポンス（`201 Created`、`status = failed`）
```json
{
  "transaction_id": "f4c2a1b0-9e7d-4b3a-8c6f-1d2e3f4a5b6c",
  "kind": "charge",
  "status": "failed",
  "amount": 2000,
  "currency": "JPY",
  "card_last4": "0000",
  "description": null,
  "error": {
    "code": "card_declined",
    "message": "The card was declined."
  },
  "created_at": "2026-06-11T02:42:00Z"
}
```

> 決済失敗は **HTTP 201** で返し、`status = failed` および `error` オブジェクトを含める。これにより取引としては記録される。

#### 失敗判定ルール（模擬）
| 条件 | `status` | `error.code` |
| --- | --- | --- |
| `card_number` 末尾 4 桁 = `0000` | `failed` | `card_declined` |
| `card_number` 末尾 4 桁 = `0001` | `failed` | `insufficient_funds` |
| `card_number` 末尾 4 桁 = `0002` | `failed` | `expired_card` |
| `card_number` 末尾 4 桁 = `0119` | `failed` | `processing_error` |
| `amount` >= 1,000,000 | `failed` | `amount_too_large` |
| 上記以外 | `succeeded` | - |

#### バリデーションエラー例（`400`）
```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {
      "amount": ["Must be greater than 0."],
      "currency": ["This field is required."]
    }
  }
}
```

---

### 5.2 `POST /api/v1/payments/refund`

成功済みの取引に対して返金を行う。

#### リクエストボディ
| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `transaction_id` | string(36) | ○ | 返金対象の `transaction_id`。 |
| `amount` | number | × | 部分返金額。省略時は元取引と同額の全額返金。 |
| `reason` | string | × | 返金理由（任意）。 |

#### リクエスト例
```http
POST /api/v1/payments/refund HTTP/1.1
Host: localhost:8000
X-API-Key: pk_live_abc123...
Content-Type: application/json

{
  "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
  "reason": "customer_request"
}
```

#### 成功レスポンス（`201 Created`）
```json
{
  "transaction_id": "9aa8b7c6-1234-4def-9abc-0123456789ab",
  "kind": "refund",
  "status": "succeeded",
  "amount": 1500,
  "currency": "JPY",
  "card_last4": "4242",
  "related_transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
  "reason": "customer_request",
  "created_at": "2026-06-11T02:50:00Z"
}
```

#### ビジネスエラー例

##### 元取引が存在しない / 自分のものではない（`404 Not Found`）
```json
{
  "error": {
    "code": "transaction_not_found",
    "message": "The specified transaction was not found."
  }
}
```

##### 元取引が `succeeded` ではない（`422 Unprocessable Entity`）
```json
{
  "error": {
    "code": "refund_not_allowed",
    "message": "Only succeeded charges can be refunded."
  }
}
```

##### 既に返金済み（`409 Conflict`）
```json
{
  "error": {
    "code": "already_refunded",
    "message": "This transaction has already been refunded."
  }
}
```

##### 返金額が元取引額を超過（`400 Bad Request`）
```json
{
  "error": {
    "code": "refund_amount_exceeded",
    "message": "Refund amount exceeds the original charge amount."
  }
}
```

---

### 5.3 `GET /api/v1/payments/{transaction_id}`

取引情報を取得する。自分（API キー所有者）に紐づく取引のみ取得可能。

#### URL パスパラメータ
| パラメータ | 型 | 説明 |
| --- | --- | --- |
| `transaction_id` | string(36) | 取得対象の `transaction_id` |

#### リクエスト例
```http
GET /api/v1/payments/7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e HTTP/1.1
Host: localhost:8000
X-API-Key: pk_live_abc123...
```

#### 成功レスポンス（`200 OK`）
```json
{
  "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
  "kind": "charge",
  "status": "succeeded",
  "amount": 1500,
  "currency": "JPY",
  "card_last4": "4242",
  "description": "Order #1234",
  "related_transaction_id": null,
  "created_at": "2026-06-11T02:41:00Z"
}
```

#### 失敗レスポンス
- 自分の取引でない / 存在しない → `404 Not Found`（`transaction_not_found`）

---

### 5.4 `GET /api/v1/transactions`

自分（API キー所有者）の取引一覧を取得する。

#### クエリパラメータ
| パラメータ | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `kind` | string | × | `charge` / `refund` で絞り込み。 |
| `status` | string | × | `succeeded` / `failed` で絞り込み。 |
| `from` | string(ISO 8601) | × | 開始日時（`created_at >= from`）。 |
| `to` | string(ISO 8601) | × | 終了日時（`created_at <= to`）。 |
| `limit` | integer | × | 1〜100。デフォルト 20。 |
| `offset` | integer | × | 0 以上。デフォルト 0。 |

#### リクエスト例
```http
GET /api/v1/transactions?kind=charge&status=succeeded&limit=20 HTTP/1.1
Host: localhost:8000
X-API-Key: pk_live_abc123...
```

#### 成功レスポンス（`200 OK`）
```json
{
  "count": 42,
  "limit": 20,
  "offset": 0,
  "results": [
    {
      "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
      "kind": "charge",
      "status": "succeeded",
      "amount": 1500,
      "currency": "JPY",
      "card_last4": "4242",
      "description": "Order #1234",
      "related_transaction_id": null,
      "created_at": "2026-06-11T02:41:00Z"
    }
  ]
}
```

- `count`：絞り込み条件に合致する総件数
- `results`：今回返した取引の配列（最大 `limit` 件）

---

## 6. エラーコード一覧

| コード | HTTP | 意味 |
| --- | --- | --- |
| `unauthorized` | 401 | 認証エラー（API キー不正・欠落・無効化） |
| `forbidden` | 403 | 認可エラー（管理者が API を叩いた等） |
| `validation_error` | 400 | 入力バリデーションエラー |
| `transaction_not_found` | 404 | 取引が存在しない / 自分の取引ではない |
| `refund_not_allowed` | 422 | 返金不可（元取引が成功していない等） |
| `already_refunded` | 409 | 既に返金済み |
| `refund_amount_exceeded` | 400 | 返金額が元取引額を超過 |
| `card_declined` | 200（`failed`） | カード拒否（末尾 `0000`） |
| `insufficient_funds` | 200（`failed`） | 残高不足（末尾 `0001`） |
| `expired_card` | 200（`failed`） | カード期限切れ（末尾 `0002`） |
| `processing_error` | 200（`failed`） | 処理エラー（末尾 `0119`） |
| `amount_too_large` | 200（`failed`） | 金額過大（`amount >= 1,000,000`） |
| `internal_error` | 500 | サーバー内部エラー |

---

## 7. データモデル（API レスポンス相当）

### 7.1 Transaction オブジェクト
| フィールド | 型 | 説明 |
| --- | --- | --- |
| `transaction_id` | string(36) | UUID |
| `kind` | string | `charge` / `refund` |
| `status` | string | `succeeded` / `failed` |
| `amount` | number | 金額 |
| `currency` | string(3) | 通貨コード |
| `card_last4` | string(4) | カード下 4 桁 |
| `description` | string \| null | 任意のメモ（charge のみ） |
| `reason` | string \| null | 返金理由（refund のみ） |
| `related_transaction_id` | string(36) \| null | 関連する取引（refund のみ） |
| `error` | object \| null | 失敗時のみ。`{ code, message }` |
| `created_at` | string(ISO 8601) | 作成日時（UTC） |

---

## 8. cURL 例（疎通テスト）

### 8.1 決済リクエスト（成功）
```bash
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "amount": 1500,
    "currency": "JPY",
    "card_number": "4242424242424242"
  }'
```

### 8.2 決済リクエスト（カード拒否を強制）
```bash
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "amount": 1500,
    "currency": "JPY",
    "card_number": "4000000000000000"
  }'
```

### 8.3 取引取得
```bash
curl http://localhost:8000/api/v1/payments/7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e \
  -H "X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 8.4 返金
```bash
curl -X POST http://localhost:8000/api/v1/payments/refund \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
  -d '{
    "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
    "reason": "customer_request"
  }'
```

### 8.5 取引一覧
```bash
curl "http://localhost:8000/api/v1/transactions?kind=charge&status=succeeded&limit=10" \
  -H "X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## 9. 注意事項

- 本 API は **模擬決済** であり、実際の決済ネットワークへは接続しない。
- 入力された `card_number` の下 4 桁以外は **保存しない**（メモリ上でも下 4 桁のみ保持）。
- レートリミット・冪等性キー（`Idempotency-Key`）は本仕様の範囲外（将来拡張）。
- 取引データの長期保持期間は本仕様の範囲外（運用ポリシーで別途定義）。
