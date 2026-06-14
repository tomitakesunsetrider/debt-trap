# 決済 API 利用ガイド（一般ユーザー向け）

このドキュメントは、`debt-trap` の **模擬決済 API** を利用するアプリ開発者向けの利用ガイドです。  
Web 画面で登録した一般ユーザー（エンドユーザー）が、自分のアプリから決済機能を呼び出すために必要な情報をまとめています。

> 本 API は **検証・学習用の模擬決済** です。実際のクレジットカードへの請求は一切発生しません。

---

## 1. クイックスタート

3 ステップで最初のリクエストを送れます。

### ステップ 1: アカウントを作成する
1. ブラウザで `http://15.152.44.182/` を開きます。
2. 画面下部の **「新規登録はこちら」** をクリックします。
3. ユーザー名・メールアドレス・パスワードを入力して登録します。

> 管理者ユーザーはこの画面からは作成できません。一般ユーザー専用です。

### ステップ 2: API キーを取得する
登録が完了するとダッシュボード（`/dashboard/`）に遷移し、自分の API キーが表示されます。  
形式は次のとおりです。

```
pk_live_aB12_x9-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

- このキーは **あなた専用** の認証情報です。第三者と共有しないでください。
- ダッシュボードの「API キー再発行」ボタンで、いつでも新しいキーに更新できます（古いキーは即座に無効になります）。

### ステップ 3: 最初のリクエストを送る

```bash
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <ここに自分の API キーを貼り付け>" \
  -d '{
    "amount": 1500,
    "currency": "JPY",
    "card_number": "4242424242424242"
  }'
```

成功すると、次のような JSON が返ります。

```json
{
  "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
  "kind": "charge",
  "status": "succeeded",
  "amount": 1500,
  "currency": "JPY",
  "card_last4": "4242",
  "description": null,
  "created_at": "2026-06-11T02:41:00Z"
}
```

---

## 2. 基本情報

| 項目 | 値 |
| --- | --- |
| ベース URL（開発環境） | `http://localhost:8000` |
| API ルートパス | `/api/v1` |
| データフォーマット | JSON（`application/json`） |
| 文字コード | UTF-8 |
| 日付フォーマット | ISO 8601 UTC（例: `2026-06-11T02:41:00Z`） |

---

## 3. 認証

すべての API リクエストに、HTTP ヘッダで API キーを指定してください。

```
X-API-Key: pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
Content-Type: application/json
```

### 注意
- API キーは Web 画面で登録した **一般ユーザーのみ** が保有します。
- 管理者ユーザーは API キーを持たないため、決済 API は利用できません。
- 不正・欠落・無効化された API キーでは `401 Unauthorized` が返ります。

---

## 4. エンドポイント一覧

| メソッド | パス | 概要 |
| --- | --- | --- |
| POST | `/api/v1/payments/charge` | 決済（売上）を行う |
| POST | `/api/v1/payments/refund` | 取引を返金する |
| GET | `/api/v1/payments/{transaction_id}` | 取引情報を取得する |
| GET | `/api/v1/transactions` | 自分の取引一覧を取得する |

---

## 5. 決済する: `POST /payments/charge`

### リクエストボディ

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `amount` | number | ○ | 金額。`JPY` の場合は整数のみ。0 より大きい値。 |
| `currency` | string(3) | ○ | 通貨コード（ISO 4217）。例: `JPY`, `USD`。 |
| `card_number` | string | ○ | カード番号。下 4 桁のみ保存されます。 |
| `card_holder` | string | × | カードホルダー名。 |
| `card_exp_month` | integer | × | 有効期限の月（1〜12）。 |
| `card_exp_year` | integer | × | 有効期限の年（YYYY）。 |
| `card_cvc` | string | × | CVC（保存されません）。 |
| `description` | string | × | 自由記述のメモ（注文番号など）。 |

### 成功時のレスポンス（`201 Created`）

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

### 決済失敗時のレスポンス（`201 Created`、`status = failed`）

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

> **重要**：決済そのものが失敗した場合でも HTTP ステータスは `201` です。  
> アプリ側では `status` フィールドを確認して成功 / 失敗を判定してください。  
> HTTP 4xx / 5xx は「リクエスト形式が誤っている」「認証エラー」「サーバー側の異常」を表します。

---

## 6. テストカード一覧

模擬決済の挙動は、カード番号の **末尾 4 桁** と **金額** で決定的に切り替わります。  
本物のカードネットワークには接続されないので、安心して試せます。

### カード番号末尾による挙動

| カード番号末尾 4 桁 | 結果 | `error.code` |
| --- | --- | --- |
| `0000` | 失敗 | `card_declined` |
| `0001` | 失敗 | `insufficient_funds` |
| `0002` | 失敗 | `expired_card` |
| `0119` | 失敗 | `processing_error` |
| その他（例: `4242`） | 成功 | - |

### 金額による挙動

| 条件 | 結果 |
| --- | --- |
| `amount` <= 0 | `400 Bad Request`（バリデーションエラー） |
| `amount` >= 1,000,000 | 失敗 `amount_too_large` |
| `currency = JPY` で `amount` に小数 | `400 Bad Request` |
| `currency = USD` で小数 3 桁以上 | `400 Bad Request` |

### 試してみる例

```bash
curl -X POST http://localhost:8000/api/v1/payments/charge \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_live_xxxx" \
  -d '{ "amount": 1500, "currency": "JPY", "card_number": "4000000000000000" }'
```

末尾 `0000` のため `card_declined` で失敗するレスポンスが返ります。

---

## 7. 返金する: `POST /payments/refund`

成功している `charge` の取引を返金します。

### リクエストボディ

| フィールド | 型 | 必須 | 説明 |
| --- | --- | --- | --- |
| `transaction_id` | string(36) | ○ | 返金対象の取引 ID。 |
| `amount` | number | × | 部分返金額。省略時は元取引と同額を全額返金。 |
| `reason` | string | × | 返金理由（自由記述）。 |

### リクエスト例

```bash
curl -X POST http://localhost:8000/api/v1/payments/refund \
  -H "Content-Type: application/json" \
  -H "X-API-Key: pk_live_xxxx" \
  -d '{
    "transaction_id": "7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e",
    "reason": "customer_request"
  }'
```

### 成功時のレスポンス（`201 Created`）

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

### 返金できないケース

| 状況 | HTTP | `error.code` |
| --- | --- | --- |
| 元の取引が見つからない / 自分の取引でない | 404 | `transaction_not_found` |
| 元の取引が `succeeded` でない | 422 | `refund_not_allowed` |
| すでに返金済み | 409 | `already_refunded` |
| 返金額が元取引額を超過 | 400 | `refund_amount_exceeded` |

---

## 8. 取引を取得する: `GET /payments/{transaction_id}`

自分が作成した取引（charge / refund いずれも）を取得します。

```bash
curl http://localhost:8000/api/v1/payments/7b5e4a2c-1a3d-4f6b-9c8e-2f1a0b3c4d5e \
  -H "X-API-Key: pk_live_xxxx"
```

レスポンス（`200 OK`）：

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

> 他のユーザーの取引は取得できません（`404 Not Found` が返ります）。

---

## 9. 取引一覧を取得する: `GET /transactions`

自分の取引のみが対象です。

### クエリパラメータ

| パラメータ | 説明 | 既定値 |
| --- | --- | --- |
| `kind` | `charge` / `refund` で絞り込み | - |
| `status` | `succeeded` / `failed` で絞り込み | - |
| `from` | 開始日時（ISO 8601） | - |
| `to` | 終了日時（ISO 8601） | - |
| `limit` | 1〜100 | 20 |
| `offset` | 0 以上 | 0 |

### リクエスト例

```bash
curl "http://localhost:8000/api/v1/transactions?kind=charge&status=succeeded&limit=10" \
  -H "X-API-Key: pk_live_xxxx"
```

### レスポンス（`200 OK`）

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

- `count`：絞り込み条件に合致する全件数
- `results`：今回返した取引（最大 `limit` 件）

---

## 10. エラーハンドリング

エラー時のレスポンスボディは、すべて以下の共通形式です。

```json
{
  "error": {
    "code": "validation_error",
    "message": "Request validation failed.",
    "details": {
      "amount": ["Must be greater than 0."]
    }
  }
}
```

- `code`：機械可読のエラーコード（プログラムで分岐する用）。
- `message`：人間向けのエラーメッセージ。
- `details`：フィールド単位の詳細（バリデーションエラー時のみ）。

### 主な HTTP ステータス

| ステータス | 意味 | よくある原因 |
| --- | --- | --- |
| `200 OK` | 取得成功 | - |
| `201 Created` | 取引作成成功（`status` が `failed` の場合もある） | - |
| `400 Bad Request` | リクエスト形式の不備 | 必須フィールド欠落、型不正、金額が 0 以下 |
| `401 Unauthorized` | 認証エラー | `X-API-Key` 未指定、無効なキー |
| `403 Forbidden` | 認可エラー | 管理者キーで API 呼び出し（管理者はキーなし） |
| `404 Not Found` | リソースなし | 他人の取引、存在しない取引 ID |
| `409 Conflict` | 競合 | 二重返金など |
| `422 Unprocessable Entity` | ビジネスルール違反 | 失敗取引を返金しようとした等 |
| `500 Internal Server Error` | サーバー側の異常 | 一時的な障害（再試行可） |

### 主なエラーコード一覧

| `error.code` | 発生タイミング | HTTP |
| --- | --- | --- |
| `unauthorized` | API キーが不正・欠落 | 401 |
| `forbidden` | 権限不足 | 403 |
| `validation_error` | 入力バリデーション失敗 | 400 |
| `transaction_not_found` | 取引が見つからない | 404 |
| `refund_not_allowed` | 返金不可な取引 | 422 |
| `already_refunded` | 二重返金 | 409 |
| `refund_amount_exceeded` | 返金額が元取引額を超過 | 400 |
| `card_declined` | カード拒否（末尾 `0000`） | 201（`failed`） |
| `insufficient_funds` | 残高不足（末尾 `0001`） | 201（`failed`） |
| `expired_card` | 期限切れ（末尾 `0002`） | 201（`failed`） |
| `processing_error` | 処理エラー（末尾 `0119`） | 201（`failed`） |
| `amount_too_large` | 金額過大 | 201（`failed`） |
| `internal_error` | サーバー内部エラー | 500 |

---

## 11. コードサンプル

### Python（`requests`）

```python
import requests

API_BASE = "http://localhost:8000/api/v1"
API_KEY = "pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
}

res = requests.post(
    f"{API_BASE}/payments/charge",
    headers=headers,
    json={
        "amount": 1500,
        "currency": "JPY",
        "card_number": "4242424242424242",
        "description": "Order #1234",
    },
    timeout=10,
)
res.raise_for_status()
body = res.json()

if body["status"] == "succeeded":
    print("OK:", body["transaction_id"])
else:
    print("FAILED:", body["error"]["code"], body["error"]["message"])
```

### JavaScript（`fetch`）

```javascript
const API_BASE = "http://localhost:8000/api/v1";
const API_KEY = "pk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";

const res = await fetch(`${API_BASE}/payments/charge`, {
  method: "POST",
  headers: {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    amount: 1500,
    currency: "JPY",
    card_number: "4242424242424242",
  }),
});

const body = await res.json();
if (body.status === "succeeded") {
  console.log("OK:", body.transaction_id);
} else {
  console.log("FAILED:", body.error?.code, body.error?.message);
}
```

---

## 12. よくある質問（FAQ）

**Q. 本物のクレジットカード番号を入れても大丈夫？**  
A. 強くお勧めしません。本 API はデモ用途です。実カード番号は **絶対に** 送信しないでください。テスト用にはカード番号末尾 4 桁だけで挙動が変わる、`4242 4242 4242 4242` 等のダミー番号を使ってください。

**Q. API キーを忘れたら？**  
A. Web 画面（`/dashboard/`）からいつでも確認できます。

**Q. API キーが漏れたかも？**  
A. ダッシュボードの「API キー再発行」を実行してください。古いキーはすぐに無効になります。

**Q. なぜ決済が失敗しても HTTP 200 系で返ってくるの？**  
A. 「取引としては記録された」ことを示すためです。API リクエストの失敗（4xx / 5xx）と、決済の失敗（`status = failed`）を分けて扱えるようにしています。

**Q. 取引履歴は Web から見られる？**  
A. はい。`/me/transactions/` で自分の取引一覧を確認できます。管理者ユーザーは全ユーザーの取引を閲覧できます。

**Q. レートリミットはある？**  
A. 現状は設定されていません。将来的に追加される可能性があります。

---

## 13. サポート

不具合・要望は管理者ユーザーに連絡してください。  
詳細な内部仕様は [`api_specification.md`](./api_specification.md) を参照してください。
