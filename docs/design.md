# AI要約API 設計書

## 概要

AI要約APIは、AWS上でサーバーレスに稼働するRESTful APIサービスです。本設計書では、システムのアーキテクチャ、コンポーネント設計、データモデル、エラーハンドリング、テスト戦略について詳述します。

### 設計目標

- **サーバーレスファースト**: AWS管理サービスを活用して運用オーバーヘッドを最小化
- **シングルパーパス関数**: 各Lambda関数は特定のドメイン責任を処理
- **パフォーマンス最適化**: 厳格なレイテンシ要件を満たす（CRUD: 200ms、AI: 30-60秒）
- **コスト効率**: 従量課金モデルとDynamoDBオンデマンド価格設定
- **可観測性**: 包括的なロギング、メトリクス、分散トレーシング
- **スケーラビリティ**: 可変ワークロードに対する自動スケーリング

## アーキテクチャ

### 高レベルアーキテクチャ

```
Client Application
       ↓
  API Gateway (REST API, CORS有効)
       ↓
   ┌───┴───┬────────┐
   ↓       ↓        ↓
Memo    AI      AllMemos
Function Function Summary
(10s)   (35s)   Function(65s)
   ↓       ↓        ↓
   └───┬───┴────────┘
       ↓
   DynamoDB (MemoTable)
   Single-Table Design
   UpdatedAtIndex GSI
       
   AI Function & AllMemos → AWS Bedrock
   Summary Function         Claude Sonnet 4.6
                           (Inference Profile)
                           
   All Functions → CloudWatch
                  (Logs & Metrics)
```

### アーキテクチャ決定

#### 1. シングルテーブルDynamoDBデザイン

すべてのメモデータに単一のDynamoDBテーブルを使用：
- コスト最小化（テーブル数削減）
- アクセスパターンの簡素化（一貫したキー構造）
- GSIによる効率的なクエリ（更新タイムスタンプでのソート）

**理由**: アプリケーションは単純なデータモデル（Memoエンティティのみ）を持つため、シングルテーブル設計が最適なパフォーマンスとコスト効率を提供

#### 2. メモ操作とAI操作の分離

メモCRUD操作とAI操作を別々のLambda関数に分離：
- 異なるパフォーマンス特性（CRUD: 200ms、AI: 30-60秒）
- 異なるリソース要件（AIはより多くのメモリ/タイムアウトが必要）
- 異なるリトライ戦略（AIは指数バックオフが必要）
- 明確な関心の分離と保守性の向上

**理由**: シングルパーパス関数はサーバーレスベストプラクティスに沿い、独立したスケーリングと最適化を可能にする

#### 3. API Gatewayリクエスト検証

API Gatewayレベルで検証を実装：
- Lambda呼び出し前に無効なリクエストを拒否（コスト削減）
- 一貫したエラーレスポンスを提供
- Lambda実行時間を削減

**理由**: 早期検証により不要な計算コストを削減し、無効なリクエストのレスポンス時間を改善

#### 4. AWS Bedrock Claude for AI

外部AIサービスではなくAWS Bedrockを使用：
- すべてのデータをAWSインフラ内に保持（セキュリティ）
- AWS IAMによるアクセス制御を活用
- AWSリージョン可用性の恩恵
- 請求とコスト追跡の簡素化

**理由**: ネイティブAWS統合により、より良いセキュリティ、コンプライアンス、運用の簡素性を提供

## コンポーネント設計

### 1. API Gateway

**責任**: HTTPリクエストルーティング、リクエスト検証、レスポンスフォーマット

**エンドポイント**:
- `POST /memos` - 新しいメモを作成
- `GET /memos/{id}` - 特定のメモを取得
- `GET /memos` - すべてのメモを一覧表示（ページネーション付き）
- `PUT /memos/{id}` - メモを更新
- `DELETE /memos/{id}` - メモを削除
- `POST /memos/{id}/ask` - メモについてAIに質問
- `POST /memos/summary` - 全メモのAI要約を生成

**設定**:
- Webクライアントアクセス用のCORS有効化
- JSONスキーマを使用したリクエスト検証
- API Gatewayキャッシング無効（データ鮮度優先）
- CloudWatchロギング有効（INFOレベル）

**リクエスト検証ルール**:
- タイトル: 1-200文字、作成/更新時必須
- 内容: 1-50,000文字、作成/更新時必須
- 質問: 1-1,000文字、AI質問時必須
- ページネーション: page_size（1-100、デフォルト20）、next_token（オプション）

### 2. Memo Lambda Function

**責任**: すべてのメモCRUD操作を処理

**設定**:
- ランタイム: Python 3.13
- メモリ: 512 MB
- タイムアウト: 10秒
- 環境変数:
  - `MEMO_TABLE_NAME`: DynamoDBテーブル名
  - `LOG_LEVEL`: ロギングレベル（INFO）
  - `POWERTOOLS_SERVICE_NAME`: memo-service

**IAM権限**:
- `dynamodb:PutItem`（作成）
- `dynamodb:GetItem`（読み取り）
- `dynamodb:Query`（GSIでの一覧表示）
- `dynamodb:UpdateItem`（更新）
- `dynamodb:DeleteItem`（削除）
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**依存関係**:
- boto3（AWS SDK）
- aws-lambda-powertools（ロギング、トレーシング、メトリクス）

### 3. AI Lambda Function

**責任**: AWS Bedrock Claudeを使用してAI質問を処理

**設定**:
- ランタイム: Python 3.13
- メモリ: 1024 MB（AI処理用に高め）
- タイムアウト: 35秒（30秒AI + 5秒バッファ）
- 環境変数:
  - `MEMO_TABLE_NAME`: DynamoDBテーブル名
  - `BEDROCK_MODEL_ID`: us.anthropic.claude-sonnet-4-6（インフェレンスプロファイル）
  - `BEDROCK_REGION`: us-west-2
  - `MAX_RETRIES`: 3
  - `LOG_LEVEL`: INFO
  - `POWERTOOLS_SERVICE_NAME`: ai-service

**IAM権限**:
- `dynamodb:GetItem`（メモ読み取り）
- `bedrock:InvokeModel`（Claude呼び出し）
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`

**リトライ戦略**:
- 指数バックオフ: 1秒、2秒、4秒
- リトライ対象: ThrottlingException、ServiceUnavailableException
- リトライ対象外: ValidationException、AccessDeniedException

### 4. AllMemosSummary Lambda Function

**責任**: 全メモのAI要約を生成

**設定**:
- ランタイム: Python 3.13
- メモリ: 1024 MB
- タイムアウト: 65秒（60秒AI + 5秒バッファ）
- 環境変数:
  - `MEMO_TABLE_NAME`: DynamoDBテーブル名
  - `BEDROCK_MODEL_ID`: us.anthropic.claude-sonnet-4-6
  - `BEDROCK_REGION`: us-west-2
  - `MAX_RETRIES`: 3
  - `MAX_CONTENT_TOKENS`: 180000
  - `LOG_LEVEL`: INFO
  - `POWERTOOLS_SERVICE_NAME`: ai-summary-api

**主要コンポーネント**:

#### MemoAggregator
- 複数のメモを単一のコンテキスト文字列に集約
- トークン数に基づくコンテンツサイズ制限を適用
- 制限を超える場合、最近更新されたメモを優先
- 含まれたメモ数と総メモ数を追跡

#### BedrockService
- AWS Bedrock Claude Sonnet 4.6モデルを呼び出し
- 指数バックオフリトライロジックを実装
- 全メモ要約生成用のプロンプトを構築
- Bedrockレスポンスを解析

### 5. DynamoDB Table

**責任**: メモデータの永続化ストレージ

**テーブル設計**（シングルテーブル）:

**プライマリキー**:
- パーティションキー: `PK`（文字列） - 形式: `MEMO#{memo_id}`
- ソートキー: なし（シンプルキースキーマ）

**属性**:
- `PK`: パーティションキー（例: "MEMO#123e4567-e89b-12d3-a456-426614174000"）
- `id`: メモUUID（文字列）
- `title`: メモタイトル（文字列、1-200文字）
- `content`: メモ内容（文字列、1-50,000文字）
- `created_at`: ISO 8601タイムスタンプ（文字列）
- `updated_at`: ISO 8601タイムスタンプ（文字列）
- `entity_type`: エンティティタイプ（常に"MEMO"）

**グローバルセカンダリインデックス**（更新時刻での一覧表示用）:
- インデックス名: `UpdatedAtIndex`
- パーティションキー: `entity_type`（文字列） - 常に"MEMO"
- ソートキー: `updated_at`（文字列） - ISO 8601タイムスタンプ
- プロジェクション: ALL

**設定**:
- 課金モード: オンデマンド（リクエスト単位課金）
- ポイントインタイムリカバリ: 有効
- 暗号化: AWS管理キー（SSE）
- TTL: 無効（メモは無期限に保持）

**アクセスパターン**:
1. メモ作成: PKで`PutItem`
2. IDでメモ取得: PKで`GetItem`
3. 更新時刻でメモ一覧: UpdatedAtIndexで`Query`、降順
4. メモ更新: PKで`UpdateItem`
5. メモ削除: PKで`DeleteItem`
6. 全メモ取得: UpdatedAtIndexで`Query`（全メモ要約用）

### 6. AWS Bedrock統合

**責任**: メモ内容と質問に基づいてAI回答を生成

**モデル選択**: インフェレンスプロファイル経由のClaude Sonnet 4.6（`us.anthropic.claude-sonnet-4-6`）

**インフェレンスプロファイルの利点**:
- 複数のAWSリージョン（us-east-1、us-east-2、us-west-2）での自動負荷分散
- より高い可用性と耐障害性
- 一貫した価格設定とパフォーマンス

**プロンプト構造**（個別メモAI質問）:
```
あなたはメモ内容を分析する有用なアシスタントです。
以下のメモに基づいて、ユーザーの質問に答えてください。

メモタイトル: {title}
メモ内容: {content}

ユーザーの質問: {question}

メモの情報のみに基づいて、明確で簡潔な回答を提供してください。
```

**プロンプト構造**（全メモ要約）:
```
あなたは複数のメモを分析する有用なアシスタントです。
以下の{memo_count}件のメモに基づいて、包括的な要約を生成してください。

{aggregated_content}

全体のテーマ、パターン、重要な情報を特定してください。
```

**リクエスト形式**（Messages API）:
```json
{
  "anthropic_version": "bedrock-2023-05-31",
  "max_tokens": 2000,
  "temperature": 0.7,
  "messages": [
    {
      "role": "user",
      "content": "<prompt>"
    }
  ]
}
```

**レスポンス処理**:
- レスポンスの`content[0].text`から回答テキストを抽出
- メタデータを含める: model_id、processing_time、memo_id
- 日本語およびその他のUnicode文字をサポート（`ensure_ascii=False`）

## データモデル

### Memoオブジェクト

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Memo:
    id: str                    # UUID v4
    title: str                 # 1-200文字
    content: str               # 1-50,000文字
    created_at: datetime       # ISO 8601形式
    updated_at: datetime       # ISO 8601形式
    
    def to_dict(self) -> dict:
        """APIレスポンス用の辞書に変換"""
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def to_dynamodb_item(self) -> dict:
        """DynamoDBアイテム形式に変換"""
        return {
            'PK': f'MEMO#{self.id}',
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'entity_type': 'MEMO'  # GSI用
        }
```

### APIリクエスト/レスポンスモデル

**メモ作成リクエスト**:
```json
{
  "title": "string (1-200文字)",
  "content": "string (1-50,000文字)"
}
```

**メモ作成レスポンス**（201 Created）:
```json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp"
}
```

**メモ一覧レスポンス**（200 OK）:
```json
{
  "memos": [
    {
      "id": "uuid",
      "title": "string",
      "content": "string",
      "created_at": "ISO 8601 timestamp",
      "updated_at": "ISO 8601 timestamp"
    }
  ],
  "next_token": "base64_encoded_token or null"
}
```

**AI質問リクエスト**:
```json
{
  "question": "string (1-1,000文字)"
}
```

**AI回答レスポンス**（200 OK）:
```json
{
  "answer": "string",
  "metadata": {
    "model_id": "string",
    "processing_time_ms": "number",
    "memo_id": "uuid"
  }
}
```

**全メモ要約レスポンス**（200 OK）:
```json
{
  "summary": "string",
  "metadata": {
    "model_id": "string",
    "processing_time_ms": "number",
    "memos_included": "number",
    "memos_total": "number",
    "truncated": "boolean"
  }
}
```

**エラーレスポンス**（4xx、5xx）:
```json
{
  "error": {
    "code": "string",
    "message": "string",
    "request_id": "string"
  }
}
```

## エラーハンドリング

### エラーカテゴリとレスポンス

**1. バリデーションエラー（400 Bad Request）**
- リクエストボディの無効なJSON形式
- バリデーション失敗（タイトル/内容/質問の長さ違反）
- 必須フィールドの欠落

**2. リソース未検出（404 Not Found）**
- メモIDが存在しない
- 適用対象: GET、PUT、DELETE、POST /ask操作

**3. サービス利用不可（503 Service Unavailable）**
- リトライ後のBedrockスロットリング
- Bedrockサービス利用不可

**4. 内部サーバーエラー（500 Internal Server Error）**
- 予期しないLambda関数エラー
- DynamoDBサービスエラー（スロットリング以外）
- 未処理の例外

**5. ゲートウェイタイムアウト（504 Gateway Timeout）**
- Lambda実行が65秒を超える（API Gatewayが処理）

### リトライ戦略

**Bedrockリトライ**:
- リトライ可能なエラー: `ThrottlingException`、`ServiceUnavailableException`
- 最大リトライ回数: 3回
- バックオフ: 指数（1秒、2秒、4秒）
- リトライ不可能なエラー: 適切なエラーコードで即座に失敗

**DynamoDBリトライ**:
- boto3デフォルトリトライロジックで処理（指数バックオフで3回）
- カスタムリトライロジック不要

### エラーロギング

すべてのエラーは以下を含めてログ記録:
- エラータイプ（例外クラス名）
- エラーメッセージ
- スタックトレース（予期しないエラーの場合）
- トレーシング用のリクエストID
- コンテキスト: メモ数、処理ステージなど

## テスト戦略

### デュアルテストアプローチ

この機能には、包括的なカバレッジのために単体テストとプロパティベーステストの両方が必要：

**単体テスト**の焦点:
- 特定の例（空のメモコレクション、単一メモ、複数メモ）
- エッジケース（リトライ枯渇、タイムアウトシナリオ）
- エラー条件（DynamoDBエラー、Bedrockエラー）
- 統合ポイント（API Gatewayイベント解析、レスポンスフォーマット）

**プロパティベーステスト**の焦点:
- すべての入力にわたる普遍的なプロパティ（レスポンス構造、メモ集約）
- ランダム化された入力生成（さまざまなメモ数、コンテンツサイズ、タイムスタンプ）
- プロパティごとに100回以上の反復による包括的なカバレッジ

### プロパティベーステスト設定

**ライブラリ**: `hypothesis`（Pythonプロパティベーステストライブラリ）

**設定**:
- プロパティテストごとに最低100回の反復
- 各テストにタグ付け: `# Feature: {feature-name}, Property {number}: {property_text}`
- 現実的なデータを持つMemoオブジェクト用のカスタムジェネレータを使用
- 適切なストラテジーで`@given`デコレータを使用

### テスト組織

```
tests/
├── unit/
│   ├── test_memo_operations.py
│   ├── test_ai_operations.py
│   ├── test_all_memos_summary.py
│   ├── test_validation.py
│   └── test_error_handling.py
├── property/
│   ├── test_memo_properties.py
│   ├── test_ai_properties.py
│   ├── test_all_memos_summary_properties.py
│   └── test_pagination_properties.py
├── integration/
│   ├── test_api_endpoints.py
│   ├── test_dynamodb_integration.py
│   └── test_bedrock_integration.py
└── performance/
    ├── test_latency.py
    └── load_test_config.py
```

### テストカバレッジ目標

- 単体テストカバレッジ: > 80%
- プロパティテストカバレッジ: すべてのプロパティを実装
- 統合テストカバレッジ: すべてのAPIエンドポイント
- クリティカルパスカバレッジ: 100%（作成、読み取り、更新、削除、質問、要約）

## デプロイメント

### AWS SAM

**デプロイコマンド**:
```bash
# 依存関係のインストール
pip install -r requirements.txt

# Lambda関数のビルド
sam build

# AWSへのデプロイ
sam deploy --guided

# ローカルでAPIを実行
sam local start-api

# Lambda関数をローカルで呼び出し
sam local invoke FunctionName -e events/event.json
```

### 継続的インテグレーション

**CIパイプライン**（GitHub Actions / AWS CodePipeline）:
1. 単体テストを実行（高速フィードバック）
2. 100回の反復でプロパティテストを実行
3. 統合テストを実行（テストAWSアカウントで）
4. ステージング環境にデプロイ
5. ステージングに対してスモークテストを実行
6. 本番デプロイの手動承認

## 監視とアラート

### CloudWatchメトリクス

- リクエスト数（エンドポイント別）
- エラー数（エラータイプ別）
- 処理時間（p50、p95、p99）
- 処理されたメモ数
- Lambda同時実行数
- DynamoDBスロットリングイベント

### CloudWatchアラーム

- エラー率 > 5%（5分間）
- p95レイテンシ > しきい値（CRUD: 200ms、AI: 30秒）
- Lambda同時実行数 > 80%
- DynamoDBスロットリング > 0

### ログ分析

- CloudWatch Insightsクエリによるエラーパターン分析
- リクエストIDによる分散トレーシング
- パフォーマンスボトルネックの特定

## セキュリティ考慮事項

### IAMロール

- 最小権限の原則に従う
- 各Lambda関数に個別のIAMロール
- リソースレベルの権限（特定のDynamoDBテーブル、Bedrockモデル）

### データ保護

- 転送中の暗号化（HTTPS）
- 保存時の暗号化（DynamoDB SSE）
- 機密データのAWS Secrets Manager使用

### API保護

- API Gatewayリクエスト検証
- レート制限（スロットリング）
- CORS設定
- 将来の拡張: Lambda Authorizer、AWS WAF

## コスト最適化

### Lambda

- メモリ割り当ての適切なサイズ設定（512MB、1024MB）
- コールドスタート影響の最小化（デプロイパッケージサイズの削減）
- 必要な場合のみプロビジョニング済み同時実行数を使用

### DynamoDB

- オンデマンド価格設定（予測不可能なワークロード用）
- 効率的なクエリパターン（GSI使用）
- 適切なデータモデリング（ホットパーティション回避）

### Bedrock

- 効率的なプロンプト設計（トークン使用量の最小化）
- インフェレンスプロファイル使用（コスト最適化）
- 適切なmax_tokens設定

### 一般

- 未使用リソースの定期的なクリーンアップ
- CloudWatchログの保持期間設定
- コスト異常検知アラート
