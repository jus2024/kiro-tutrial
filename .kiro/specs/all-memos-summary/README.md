# All Memos Summary Feature

全メモ要約機能は、システムに保存されている全てのメモを対象にAI（AWS Bedrock Claude Sonnet 4.6）による包括的な要約を生成する機能です。大量のメモから重要な情報を抽出し、全体像を把握するために使用されます。

## 機能概要

- 全メモを一括で取得し、AI要約を生成
- コンテンツサイズ制限を考慮した自動優先順位付け（最新のメモを優先）
- 空のメモコレクションの適切な処理
- リトライロジックによる高い信頼性
- 構造化ログとCloudWatchメトリクスによる監視

## API エンドポイント

### POST /memos/summary

全メモの要約を生成します。

**リクエスト:**

```bash
POST /memos/summary
Content-Type: application/json

{}
```

リクエストボディは空のJSONオブジェクト `{}` を送信します。

**成功レスポンス (200 OK):**

```json
{
  "summary": "あなたのメモには主に3つのテーマがあります：1) プロジェクト管理に関するタスクとマイルストーン、2) 技術的な学習メモとコードスニペット、3) 個人的なアイデアと将来の計画。最近のメモでは、AWS Lambdaを使用したサーバーレスアーキテクチャの実装に焦点を当てています...",
  "metadata": {
    "model_id": "us.anthropic.claude-sonnet-4-6",
    "processing_time_ms": 3245,
    "memos_included": 50,
    "memos_total": 50,
    "truncated": false
  }
}
```

**空のメモコレクションの場合 (200 OK):**

```json
{
  "summary": "メモが存在しないため、要約を生成できません。",
  "metadata": {
    "model_id": "us.anthropic.claude-sonnet-4-6",
    "processing_time_ms": 12,
    "memos_included": 0,
    "memos_total": 0,
    "truncated": false
  }
}
```

**エラーレスポンス:**

```json
{
  "error": {
    "code": "ServiceUnavailable",
    "message": "AI service temporarily unavailable. Please try again later.",
    "request_id": "abc-123-def-456"
  }
}
```

### レスポンスフィールド

| フィールド | 型 | 説明 |
|----------|-----|------|
| `summary` | string | AI生成の要約テキスト |
| `metadata.model_id` | string | 使用されたBedrockモデルID |
| `metadata.processing_time_ms` | integer | 処理時間（ミリ秒） |
| `metadata.memos_included` | integer | 要約に含まれたメモの数 |
| `metadata.memos_total` | integer | システム内の総メモ数 |
| `metadata.truncated` | boolean | コンテンツ制限により一部のメモが除外されたか |

### HTTPステータスコード

| コード | 説明 |
|-------|------|
| 200 | 成功（要約生成完了） |
| 400 | リクエストフォーマットエラー |
| 500 | 内部サーバーエラー（DynamoDBエラーなど） |
| 503 | サービス利用不可（Bedrockリトライ失敗） |
| 504 | タイムアウト（65秒超過） |

## 使用例

### curl

```bash
# API URLを環境変数に設定
export API_URL="https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev"

# 全メモの要約を生成
curl -X POST $API_URL/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}'

# レスポンスを整形して表示
curl -X POST $API_URL/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}' | jq .

# 見やすく整形して表示（format_summary.pyを使用）
curl -X POST $API_URL/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}' | python3 scripts/format_summary.py
```

### Python

```python
import requests
import json

api_url = "https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev"

# 全メモの要約を生成
response = requests.post(
    f"{api_url}/memos/summary",
    headers={"Content-Type": "application/json"},
    json={}
)

if response.status_code == 200:
    data = response.json()
    print(f"要約: {data['summary']}")
    print(f"処理時間: {data['metadata']['processing_time_ms']}ms")
    print(f"メモ数: {data['metadata']['memos_included']}/{data['metadata']['memos_total']}")
else:
    error = response.json()
    print(f"エラー: {error['error']['message']}")
```

### JavaScript (fetch)

```javascript
const apiUrl = "https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev";

async function generateSummary() {
  try {
    const response = await fetch(`${apiUrl}/memos/summary`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({})
    });

    if (response.ok) {
      const data = await response.json();
      console.log('要約:', data.summary);
      console.log('処理時間:', data.metadata.processing_time_ms, 'ms');
      console.log('メモ数:', `${data.metadata.memos_included}/${data.metadata.memos_total}`);
    } else {
      const error = await response.json();
      console.error('エラー:', error.error.message);
    }
  } catch (error) {
    console.error('リクエストエラー:', error);
  }
}

generateSummary();
```

## ユーティリティスクリプト

### 要約結果の整形表示

プロジェクトには要約結果を見やすく表示するための `format_summary.py` スクリプトが含まれています。

**使用方法:**

```bash
# パイプで直接整形
curl -X POST $API_URL/memos/summary -d '{}' | python3 scripts/format_summary.py

# ファイルから読み込んで整形
curl -X POST $API_URL/memos/summary -d '{}' > response.json
python3 scripts/format_summary.py response.json

# ヘルプ表示
python3 scripts/format_summary.py --help
```

**出力例:**

```
================================================================================
📝 メモ要約結果
================================================================================

📊 処理情報:
  • 処理時間: 3.25秒
  • 要約対象: 50/50件のメモ
  • モデル: us.anthropic.claude-sonnet-4-6
  • 切り詰め: なし

--------------------------------------------------------------------------------

📄 要約内容:

あなたのメモには主に3つのテーマがあります：1) プロジェクト管理に関する
タスクとマイルストーン、2) 技術的な学習メモとコードスニペット、3) 個人的な
アイデアと将来の計画。最近のメモでは、AWS Lambdaを使用したサーバーレス
アーキテクチャの実装に焦点を当てています...

================================================================================
```

**エラー表示:**

エラーレスポンスも適切に整形されます：

```
================================================================================
❌ エラー
================================================================================

コード: ServiceUnavailable
メッセージ: AI service temporarily unavailable. Please try again later.
リクエストID: abc-123-def-456

================================================================================
```

## アーキテクチャ

### コンポーネント構成

```
Client
  ↓
API Gateway (/memos/summary)
  ↓
AllMemosSummaryFunction (Lambda)
  ↓
  ├─→ DynamoDB (MemoTable) - 全メモ取得
  ├─→ MemoAggregator - メモ集約・優先順位付け
  ├─→ BedrockService - AI要約生成
  └─→ CloudWatch - ログ・メトリクス
```

### 主要コンポーネント

1. **AllMemosSummaryFunction** (`src/functions/all_memos_summary/handler.py`)
   - Lambda関数ハンドラー
   - リクエスト処理、エラーハンドリング、レスポンス生成

2. **MemoAggregator** (`src/services/memo_aggregator.py`)
   - メモの集約とコンテンツサイズ制限の適用
   - 最新のメモを優先的に選択

3. **BedrockService** (`src/services/bedrock_service.py`)
   - AWS Bedrock Claude Sonnet 4.6の呼び出し
   - エクスポネンシャルバックオフによるリトライロジック

## 環境変数

Lambda関数で使用される環境変数:

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `MEMO_TABLE_NAME` | (自動設定) | DynamoDBテーブル名 |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-6` | Bedrockモデル識別子 |
| `BEDROCK_REGION` | `us-west-2` | Bedrockサービスのリージョン |
| `MAX_RETRIES` | `3` | Bedrockリトライ回数 |
| `MAX_CONTENT_TOKENS` | `180000` | AI処理の最大トークン数 |
| `LOG_LEVEL` | `INFO` | ログレベル |
| `POWERTOOLS_SERVICE_NAME` | `ai-summary-api` | サービス名（ログ用） |

## デプロイ

この機能は既存のAI要約APIに統合されており、メインのSAMテンプレートに含まれています。

### 初回デプロイ

```bash
# ビルド
sam build

# デプロイ（対話形式）
sam deploy --guided
```

### 更新デプロイ

```bash
# ビルドとデプロイ
sam build && sam deploy
```

### 環境指定デプロイ

```bash
# staging環境にデプロイ
sam deploy --parameter-overrides Environment=staging

# production環境にデプロイ
sam deploy --parameter-overrides Environment=prod
```

## ローカルテスト

### SAM Local でテスト

```bash
# ローカルAPIを起動
sam local start-api

# 別のターミナルでリクエスト送信
curl -X POST http://localhost:3000/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Lambda関数を直接実行

```bash
# イベントファイルを作成
echo '{"body": "{}"}' > events/all_memos_summary.json

# Lambda関数を実行
sam local invoke AllMemosSummaryFunction -e events/all_memos_summary.json
```

## テスト

### ユニットテスト

```bash
# ハンドラーのテスト
pytest tests/unit/test_all_memos_summary_handler.py -v

# MemoAggregatorのテスト
pytest tests/unit/test_memo_aggregator.py -v

# BedrockServiceのテスト
pytest tests/unit/test_bedrock_service.py -v
```

### プロパティベーステスト

```bash
# 全プロパティテストを実行
pytest tests/property/test_all_memos_summary_properties.py -v

# 特定のプロパティテストを実行
pytest tests/property/test_all_memos_summary_properties.py::test_response_structure_completeness -v
```

### 全テスト実行

```bash
# カバレッジ付きで全テスト実行
pytest --cov=src tests/ -v

# HTMLカバレッジレポート生成
pytest --cov=src --cov-report=html tests/
```

## モニタリング

### CloudWatch Logs

```bash
# ログをリアルタイムで確認
sam logs -n AllMemosSummaryFunction --tail

# 特定期間のログを確認
sam logs -n AllMemosSummaryFunction --start-time '10min ago'

# エラーログのみフィルタ
sam logs -n AllMemosSummaryFunction --filter 'ERROR'
```

### CloudWatch Metrics

以下のカスタムメトリクスが記録されます:

- **RequestCount**: リクエスト数（ディメンション: endpoint=/memos/summary）
- **ProcessingTime**: 処理時間（単位: ミリ秒）
- **MemosProcessed**: 処理されたメモ数
- **ErrorCount**: エラー数（ディメンション: error_type）

### ログ構造

成功時のログ例:
```json
{
  "level": "INFO",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "request_id": "abc-123-def",
  "message": "Summary generated successfully",
  "memos_processed": 50,
  "processing_time_ms": 3245,
  "status": "success"
}
```

エラー時のログ例:
```json
{
  "level": "ERROR",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "request_id": "abc-123-def",
  "error_type": "ServiceUnavailableError",
  "error_message": "AI service temporarily unavailable",
  "context": {
    "memos_retrieved": 50,
    "stage": "bedrock_invocation",
    "retry_attempt": 3
  },
  "stack_trace": "..."
}
```

## パフォーマンス

### 処理時間

- **通常**: 2-5秒（メモ数50件程度）
- **大量メモ**: 5-15秒（メモ数100-500件）
- **最大**: 60秒（タイムアウト前）

### コンテンツ制限

- **最大トークン数**: 180,000トークン（約720,000文字）
- **制限超過時**: 最新のメモを優先的に選択
- **truncatedフラグ**: レスポンスで制限適用の有無を確認可能

### Lambda設定

- **タイムアウト**: 65秒
- **メモリ**: 1024MB
- **ランタイム**: Python 3.13

## エラーハンドリング

### リトライロジック

Bedrockの一時的なエラーに対して自動リトライを実行:

- **リトライ対象エラー**: `ThrottlingException`, `ServiceUnavailableException`
- **リトライ回数**: 最大3回
- **バックオフ**: エクスポネンシャル（1秒、2秒、4秒）

### エラーコード

| コード | 説明 | 対処方法 |
|--------|------|---------|
| `ValidationError` | リクエストフォーマットエラー | リクエストボディを確認 |
| `ServiceUnavailable` | Bedrockサービス利用不可 | 時間をおいて再試行 |
| `InternalError` | 内部サーバーエラー | ログを確認、サポートに連絡 |

## トラブルシューティング

### 問題: タイムアウトエラー (504)

**原因**: メモ数が非常に多い、またはBedrockの応答が遅い

**対処**:
1. CloudWatch Logsでログを確認
2. メモ数を確認（`GET /memos`で総数を取得）
3. 時間をおいて再試行

### 問題: ServiceUnavailable エラー (503)

**原因**: Bedrockのスロットリングまたは一時的な障害

**対処**:
1. 数分待ってから再試行
2. AWS Service Health Dashboardでステータス確認
3. 継続する場合はAWSサポートに連絡

### 問題: 要約が一部のメモしか含まない

**原因**: コンテンツサイズ制限により古いメモが除外された

**確認**:
- レスポンスの`metadata.truncated`が`true`
- `metadata.memos_included` < `metadata.memos_total`

**対処**: これは正常な動作です。最新のメモが優先的に要約に含まれます。

## セキュリティ

### IAM権限

Lambda関数に必要な権限:

```yaml
Policies:
  - DynamoDB:
      - dynamodb:Query
      - dynamodb:Scan
  - Bedrock:
      - bedrock:InvokeModel
  - CloudWatch:
      - logs:CreateLogGroup
      - logs:CreateLogStream
      - logs:PutLogEvents
      - cloudwatch:PutMetricData
```

### CORS設定

API GatewayでCORSが有効化されています:

- **AllowOrigin**: `*`（本番環境では特定のドメインに制限推奨）
- **AllowMethods**: `GET, POST, PUT, DELETE, OPTIONS`
- **AllowHeaders**: `Content-Type, X-Amz-Date, Authorization, X-Api-Key, X-Amz-Security-Token`

## 制限事項

1. **コンテンツサイズ**: 最大180,000トークン（約720,000文字）
2. **タイムアウト**: 65秒
3. **同時実行**: Lambda同時実行数の制限に依存
4. **リトライ**: Bedrockエラーに対して最大3回

## 今後の拡張予定

- フィルタパラメータのサポート（日付範囲、タグなど）
- 要約スタイルのカスタマイズ
- 複数言語サポート
- キャッシング機能

## 関連ドキュメント

- [Requirements Document](.kiro/specs/all-memos-summary/requirements.md)
- [Design Document](.kiro/specs/all-memos-summary/design.md)
- [Tasks Document](.kiro/specs/all-memos-summary/tasks.md)
- [Main README](../../../README.md)

## サポート

問題が発生した場合:

1. CloudWatch Logsでエラーログを確認
2. `request_id`を記録
3. 開発チームに連絡（request_idを含める）
