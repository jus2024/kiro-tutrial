# インフラストラクチャドキュメント

## 概要

本ドキュメントでは、AWS SAMを使用してデプロイされるAI要約APIのAWSインフラストラクチャについて説明します。

## AWSリソース

### DynamoDB Table: MemoTable

**目的**: シングルテーブルデザインを使用したメモデータの永続化ストレージ

**設定**:
- テーブル名: `{Environment}-ai-summary-memos`
- 課金モード: PAY_PER_REQUEST（オンデマンド）
- パーティションキー: `PK`（文字列） - 形式: `MEMO#{memo_id}`
- ポイントインタイムリカバリ: 有効
- 暗号化: AWS管理キー（SSE）

**グローバルセカンダリインデックス**: UpdatedAtIndex
- パーティションキー: `entity_type`（文字列） - 常に"MEMO"
- ソートキー: `updated_at`（文字列） - ISO 8601タイムスタンプ
- プロジェクション: ALL
- 目的: 更新時刻でソートされたメモ一覧を可能にする

**属性**:
- `PK`: パーティションキー（例: "MEMO#123e4567-e89b-12d3-a456-426614174000"）
- `id`: メモUUID
- `title`: メモタイトル（1-200文字）
- `content`: メモ内容（1-50,000文字）
- `created_at`: ISO 8601タイムスタンプ
- `updated_at`: ISO 8601タイムスタンプ
- `entity_type`: 常に"MEMO"（GSI用）

**アクセスパターン**:
1. メモ作成: PKで`PutItem`
2. IDでメモ取得: PKで`GetItem`
3. 更新時刻でメモ一覧: UpdatedAtIndexで`Query`、降順
4. メモ更新: PKで`UpdateItem`
5. メモ削除: PKで`DeleteItem`
6. 全メモ取得: UpdatedAtIndexで`Query`（全メモ要約用）

### Lambda Function: MemoFunction

**目的**: メモCRUD操作を処理

**設定**:
- 関数名: `{Environment}-ai-summary-memo-function`
- ランタイム: Python 3.13
- メモリ: 512 MB
- タイムアウト: 10秒
- ハンドラー: `handler.lambda_handler`

**環境変数**:
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `LOG_LEVEL`: INFO
- `POWERTOOLS_SERVICE_NAME`: memo-service

**IAM権限**:
- DynamoDB: MemoTableに対するPutItem、GetItem、Query、UpdateItem、DeleteItem
- DynamoDB: UpdatedAtIndex GSIに対するQuery
- CloudWatch: CreateLogGroup、CreateLogStream、PutLogEvents
- X-Ray: PutTraceSegments、PutTelemetryRecords

**APIイベント**:
- POST /memos - メモ作成
- GET /memos/{id} - メモ取得
- GET /memos - メモ一覧
- PUT /memos/{id} - メモ更新
- DELETE /memos/{id} - メモ削除

### Lambda Function: AIFunction

**目的**: AWS Bedrockを使用したAI質問応答を処理

**設定**:
- 関数名: `{Environment}-ai-summary-ai-function`
- ランタイム: Python 3.13
- メモリ: 1024 MB
- タイムアウト: 35秒
- ハンドラー: `handler.lambda_handler`

**環境変数**:
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `BEDROCK_MODEL_ID`: us.anthropic.claude-sonnet-4-6（インフェレンスプロファイル）
- `BEDROCK_REGION`: us-west-2
- `MAX_RETRIES`: 3
- `LOG_LEVEL`: INFO
- `POWERTOOLS_SERVICE_NAME`: ai-service

**IAM権限**:
- DynamoDB: MemoTableに対するGetItem
- Bedrock: InvokeModel（インフェレンスプロファイル: us.anthropic.claude-sonnet-4-6）
- CloudWatch: CreateLogGroup、CreateLogStream、PutLogEvents
- X-Ray: PutTraceSegments、PutTelemetryRecords

**APIイベント**:
- POST /memos/{id}/ask - メモについてAIに質問

**リトライ戦略**:
- 指数バックオフ: 1秒、2秒、4秒
- リトライ対象: ThrottlingException、ServiceUnavailableException
- 最大リトライ回数: 3回

### Lambda Function: AllMemosSummaryFunction

**目的**: 全メモのAI要約を生成

**設定**:
- 関数名: `{Environment}-ai-summary-all-memos-function`
- ランタイム: Python 3.13
- メモリ: 1024 MB
- タイムアウト: 65秒
- ハンドラー: `handler.lambda_handler`

**環境変数**:
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `BEDROCK_MODEL_ID`: us.anthropic.claude-sonnet-4-6
- `BEDROCK_REGION`: us-west-2
- `MAX_RETRIES`: 3
- `MAX_CONTENT_TOKENS`: 180000
- `LOG_LEVEL`: INFO
- `POWERTOOLS_SERVICE_NAME`: ai-summary-api

**IAM権限**:
- DynamoDB: MemoTableに対するQuery（UpdatedAtIndex GSI経由）
- Bedrock: InvokeModel（インフェレンスプロファイル: us.anthropic.claude-sonnet-4-6）
- CloudWatch: CreateLogGroup、CreateLogStream、PutLogEvents
- X-Ray: PutTraceSegments、PutTelemetryRecords

**APIイベント**:
- POST /memos/summary - 全メモのAI要約生成

**主要コンポーネント**:
- MemoAggregator: メモ集約とトークン制限管理
- BedrockService: Bedrock呼び出しとリトライロジック

### API Gateway: ApiGateway

**目的**: クライアントアクセス用のRESTful APIエンドポイント

**設定**:
- API名: `{Environment}-ai-summary-api`
- ステージ名: {Environment}
- トレーシング: 有効（X-Ray）
- ロギングレベル: INFO
- データトレース: 有効
- メトリクス: 有効

**CORS設定**:
- 許可メソッド: GET、POST、PUT、DELETE、OPTIONS
- 許可ヘッダー: Content-Type、X-Amz-Date、Authorization、X-Api-Key、X-Amz-Security-Token
- 許可オリジン: *（本番環境では適切に設定）

**アクセスログ**:
- 形式: リクエストID、HTTPメソッド、パス、ステータス、レスポンス長、リクエスト時間
- 送信先: CloudWatch Log Group

**リクエスト検証**:
- タイトル: 1-200文字、作成/更新時必須
- 内容: 1-50,000文字、作成/更新時必須
- 質問: 1-1,000文字、AI質問時必須

### CloudWatch Log Groups

**ApiGatewayLogGroup**:
- ログループ名: `/aws/apigateway/{Environment}-ai-summary-api`
- 保持期間: 7日

**MemoFunctionLogGroup**:
- ログループ名: `/aws/lambda/{Environment}-ai-summary-memo-function`
- 保持期間: 7日

**AIFunctionLogGroup**:
- ログループ名: `/aws/lambda/{Environment}-ai-summary-ai-function`
- 保持期間: 7日

**AllMemosSummaryFunctionLogGroup**:
- ログループ名: `/aws/lambda/{Environment}-ai-summary-all-memos-function`
- 保持期間: 7日

## スタック出力

### ApiEndpoint
- 説明: API GatewayエンドポイントURL
- 形式: `https://{ApiGatewayId}.execute-api.{Region}.amazonaws.com/{Environment}`
- エクスポート名: `{Environment}-ai-summary-api-endpoint`

### MemoTableName
- 説明: メモ用DynamoDBテーブル名
- エクスポート名: `{Environment}-ai-summary-memo-table`

### MemoFunctionArn
- 説明: Memo Lambda関数ARN
- エクスポート名: `{Environment}-ai-summary-memo-function-arn`

### AIFunctionArn
- 説明: AI Lambda関数ARN
- エクスポート名: `{Environment}-ai-summary-ai-function-arn`

### AllMemosSummaryFunctionArn
- 説明: AllMemosSummary Lambda関数ARN
- エクスポート名: `{Environment}-ai-summary-all-memos-function-arn`

## デプロイメント

### 前提条件
- 適切な認証情報で設定されたAWS CLI
- AWS SAM CLIインストール済み
- CloudFormationスタック、Lambda関数、DynamoDBテーブル、API Gateway、IAMロールを作成するIAM権限
- AWS Bedrockへのアクセス権限（us-west-2リージョン）

### デプロイコマンド

**初回デプロイ（対話形式）**:
```bash
sam build
sam deploy --guided
```

**2回目以降のデプロイ**:
```bash
sam build
sam deploy
```

**環境指定デプロイ**:
```bash
sam deploy --parameter-overrides Environment=dev
```

### 環境

- **dev**: 開発環境
- **staging**: ステージング環境
- **prod**: 本番環境

### デプロイメントパラメータ

| パラメータ | 説明 | デフォルト値 |
|-----------|------|------------|
| Environment | デプロイ環境 | dev |
| MemoFunctionMemory | Memo関数のメモリ（MB） | 512 |
| AIFunctionMemory | AI関数のメモリ（MB） | 1024 |
| AllMemosFunctionMemory | AllMemos関数のメモリ（MB） | 1024 |
| LogRetentionDays | CloudWatchログ保持期間 | 7 |

## コスト見積もり

### DynamoDB
- 課金モード: オンデマンド
- コスト: リクエスト単位課金（読み取り/書き込み）
- 見積もり: 書き込み100万リクエストあたり$1.25、読み取り100万リクエストあたり$0.25
- ストレージ: GBあたり$0.25/月

### Lambda

**Memo Function**:
- メモリ: 512 MB
- 平均実行時間: ~100ms
- 見積もり: 100万リクエストで約$0.20

**AI Function**:
- メモリ: 1024 MB
- 平均実行時間: ~5秒
- 見積もり: 10万リクエストで約$8.33

**AllMemosSummary Function**:
- メモリ: 1024 MB
- 平均実行時間: ~30秒
- 見積もり: 1万リクエストで約$5.00

**無料利用枠**: 月間100万リクエスト、400,000 GB秒/月

### API Gateway
- コスト: APIコール単位課金
- 見積もり: 100万リクエストあたり$3.50
- 無料利用枠: 月間100万リクエスト（最初の12ヶ月）

### CloudWatch
- ログ: 取り込みGBあたり$0.50
- 保持期間: 7日
- 見積もり: 通常使用で月間$5未満

### AWS Bedrock
- コスト: トークン単位課金（入力/出力）
- モデル: Claude Sonnet 4.6（インフェレンスプロファイル経由）
- 見積もり:
  - 入力: 100万トークンあたり$3.00
  - 出力: 100万トークンあたり$15.00
- 使用量により変動

### 月間コスト見積もり例

**低使用量シナリオ**（月間1,000リクエスト）:
- DynamoDB: $1
- Lambda: $1
- API Gateway: 無料枠内
- Bedrock: $5-10
- CloudWatch: $1
- **合計: 約$8-13/月**

**中使用量シナリオ**（月間10,000リクエスト）:
- DynamoDB: $5
- Lambda: $10
- API Gateway: $1
- Bedrock: $50-100
- CloudWatch: $3
- **合計: 約$69-119/月**

**高使用量シナリオ**（月間100,000リクエスト）:
- DynamoDB: $30
- Lambda: $100
- API Gateway: $35
- Bedrock: $500-1,000
- CloudWatch: $10
- **合計: 約$675-1,175/月**

## セキュリティ考慮事項

### IAMロール

**最小権限の原則**:
- 各Lambda関数に個別のIAMロール
- リソースレベルの権限（特定のDynamoDBテーブル、Bedrockモデル）
- ワイルドカード権限の回避

**推奨事項**:
- 本番環境では特定のBedrockモデルARNを指定
- CloudWatchログへのアクセスを制限
- 定期的なIAM権限レビュー

### 暗号化

**保存時の暗号化**:
- DynamoDB: AWS管理キーによるサーバーサイド暗号化
- Lambda: 環境変数の保存時暗号化
- CloudWatch Logs: デフォルトで暗号化

**転送中の暗号化**:
- API Gateway: HTTPS必須
- Lambda-DynamoDB: TLS 1.2以上
- Lambda-Bedrock: TLS 1.2以上

### ネットワーク

**現在の構成**:
- Lambda関数はAWS管理VPCで実行
- VPC設定不要（パブリックAWSサービスのみアクセス）

**本番環境の推奨事項**:
- プライベートリソースへのアクセスが必要な場合はVPC設定を検討
- VPCエンドポイント使用でコスト削減とセキュリティ向上
- セキュリティグループとNACLの適切な設定

### API保護

**実装済み**:
- API Gatewayリクエスト検証
- CORS設定
- CloudWatchロギング

**今後の拡張**:
- Lambda Authorizer（認証/認可）
- AWS WAF（Webアプリケーションファイアウォール）
- API Gatewayリソースポリシー
- レート制限とスロットリング設定

## 監視とアラート

### 推奨CloudWatchアラーム

**Memo Function**:
- エラー率 > 5%（5分間）
- 実行時間 > 8秒（タイムアウトの80%）
- スロットル > 0
- 同時実行数 > 800（制限の80%）

**AI Function**:
- エラー率 > 10%（5分間）
- 実行時間 > 30秒（タイムアウトの85%）
- スロットル > 0
- 同時実行数 > 800

**AllMemosSummary Function**:
- エラー率 > 10%（5分間）
- 実行時間 > 55秒（タイムアウトの85%）
- スロットル > 0

**DynamoDB**:
- ユーザーエラー > しきい値
- システムエラー > 0
- スロットリングイベント > 0（オンデマンドでは稀）

**API Gateway**:
- 5xxエラー > しきい値
- レイテンシ > 1秒（p99）
- 4xxエラー率 > 20%

### メトリクスダッシュボード

**推奨メトリクス**:
- APIリクエスト数（エンドポイント別）
- Lambda実行時間（関数別、p50/p95/p99）
- エラー率（関数別、エラータイプ別）
- DynamoDB読み取り/書き込みキャパシティ
- Bedrock呼び出し数とレイテンシ
- コスト（サービス別）

### ログ分析

**CloudWatch Insights クエリ例**:

```sql
# エラーログの抽出
fields @timestamp, @message
| filter @message like /ERROR/
| sort @timestamp desc
| limit 100

# レイテンシ分析
fields @timestamp, @duration
| stats avg(@duration), max(@duration), pct(@duration, 95) by bin(5m)

# エンドポイント別リクエスト数
fields @timestamp, httpMethod, path
| stats count() by httpMethod, path
```

## ディザスタリカバリ

### バックアップ戦略

**DynamoDB**:
- ポイントインタイムリカバリ有効（35日間）
- 自動バックアップ（継続的）
- オンデマンドバックアップ（手動）

**Lambda**:
- コードはSAMによりS3に保存
- バージョニング有効化推奨

**インフラストラクチャ**:
- SAMテンプレートをバージョン管理（Git）
- 環境変数とパラメータの文書化

### リカバリ手順

**データリカバリ**:
1. DynamoDBテーブルをポイントインタイムバックアップから復元
2. 復元されたテーブルの検証
3. 必要に応じてテーブル名を更新

**アプリケーションリカバリ**:
1. SAMを使用してLambda関数を再デプロイ
2. API Gatewayエンドポイントの検証
3. 統合テストの実行
4. 段階的なトラフィック切り替え

**RTO/RPO目標**:
- RTO（目標復旧時間）: 1時間
- RPO（目標復旧時点）: 5分（ポイントインタイムリカバリ）

## メンテナンス

### 定期タスク

**日次**:
- CloudWatchログのエラー確認
- メトリクスダッシュボードの確認

**週次**:
- コストと使用量メトリクスのレビュー
- アラーム状態の確認

**月次**:
- Lambdaランタイムバージョンの確認と更新計画
- requirements.txtの依存関係更新
- セキュリティパッチの適用

**四半期**:
- IAM権限のレビューとローテーション
- ディザスタリカバリ手順のテスト
- パフォーマンスチューニング

### スケーリング考慮事項

**DynamoDB**:
- オンデマンドスケーリングが自動的にトラフィックを処理
- ホットパーティション回避のためのキー設計
- GSIのスケーリングも自動

**Lambda**:
- 同時実行制限（デフォルト1,000、増加可能）
- 予約済み同時実行数の設定（オプション）
- プロビジョニング済み同時実行数（コールドスタート回避）

**API Gateway**:
- デフォルトスロットル制限（10,000リクエスト/秒）
- バーストキャパシティ（5,000リクエスト）
- 必要に応じて制限の引き上げをリクエスト

**Bedrock**:
- インフェレンスプロファイルによる自動負荷分散
- リージョン間フェイルオーバー
- クォータ制限の監視と引き上げリクエスト

## トラブルシューティング

### よくある問題と解決策

**1. Lambda タイムアウト**
- 症状: 504 Gateway Timeout、Lambda実行時間がタイムアウトに達する
- 原因: AI処理が長すぎる、DynamoDB接続遅延、コールドスタート
- 解決策:
  - タイムアウト設定の増加
  - メモリ割り当ての増加（CPU性能も向上）
  - プロビジョニング済み同時実行数の使用
  - コードの最適化

**2. DynamoDB スロットリング**
- 症状: ProvisionedThroughputExceededException
- 原因: 急激なトラフィック増加、ホットパーティション
- 解決策:
  - オンデマンド課金モードの確認（自動スケーリング）
  - パーティションキー設計の見直し
  - バッチ処理の実装

**3. Bedrock エラー**
- 症状: ThrottlingException、ServiceUnavailableException
- 原因: レート制限超過、サービス一時停止
- 解決策:
  - リトライロジックの確認（指数バックオフ）
  - クォータ引き上げリクエスト
  - インフェレンスプロファイル使用の確認

**4. CORS エラー**
- 症状: ブラウザコンソールでCORSエラー
- 原因: CORS設定の不備、プリフライトリクエストの失敗
- 解決策:
  - API Gateway CORS設定の確認
  - OPTIONSメソッドの有効化
  - 適切なヘッダーの設定

**5. 高コスト**
- 症状: 予想以上のAWS請求額
- 原因: Bedrock使用量、Lambda実行時間、DynamoDB書き込み
- 解決策:
  - CloudWatchコストメトリクスの確認
  - 不要なログの削減
  - Lambda実行時間の最適化
  - Bedrockプロンプトの効率化

## 参考リソース

### AWS ドキュメント
- [AWS SAM Developer Guide](https://docs.aws.amazon.com/serverless-application-model/)
- [AWS Lambda Developer Guide](https://docs.aws.amazon.com/lambda/)
- [Amazon DynamoDB Developer Guide](https://docs.aws.amazon.com/dynamodb/)
- [Amazon API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/)
- [AWS Bedrock User Guide](https://docs.aws.amazon.com/bedrock/)

### ベストプラクティス
- [Serverless Application Lens - AWS Well-Architected Framework](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/)
- [AWS Lambda Powertools Python](https://docs.powertools.aws.dev/lambda/python/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/best-practices.html)

---

最終更新: 2024年1月
