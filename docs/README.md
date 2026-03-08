# AI要約API ドキュメント

## 概要

AI要約APIは、AWS上でサーバーレスに稼働するRESTful APIサービスです。ユーザーがメモを作成・管理し、メモの内容についてAI（AWS Bedrock Claude Sonnet 4.6）に質問できる機能を提供します。

## ドキュメント構成

### 📋 [要件定義書](./requirements.md)
システムの機能要件、非機能要件、API仕様、制約事項を定義しています。

**主な内容**:
- 機能要件（メモCRUD、AI質問、全メモ要約）
- 非機能要件（パフォーマンス、スケーラビリティ、セキュリティ）
- API仕様（エンドポイント一覧、リクエスト/レスポンス形式）
- 制約事項と今後の拡張

### 🏗️ [設計書](./design.md)
システムのアーキテクチャ、コンポーネント設計、データモデル、エラーハンドリング、テスト戦略を詳述しています。

**主な内容**:
- 高レベルアーキテクチャ
- コンポーネント設計（Lambda関数、DynamoDB、Bedrock）
- データモデル
- エラーハンドリング戦略
- テスト戦略
- デプロイメント手順
- 監視とアラート
- セキュリティとコスト最適化

### 🎨 [アーキテクチャ図](./architecture/)
システムのアーキテクチャを視覚的に表現した図です。

**ファイル形式**:
- `architecture-diagram.drawio` - 編集可能なdraw.io形式
- `architecture-diagram.png` - PNG画像形式
- `architecture-diagram.svg` - SVGベクター形式

## クイックスタート

### 前提条件

- AWS CLI設定済み
- AWS SAM CLI インストール済み
- Python 3.13
- AWS アカウント（Bedrock有効化済み）

### ローカル開発

```bash
# 依存関係のインストール
pip install -r requirements.txt

# Lambda関数のビルド
sam build

# ローカルでAPIを起動
sam local start-api

# 別のターミナルでテスト
curl http://localhost:3000/memos
```

### デプロイ

```bash
# 初回デプロイ（対話形式）
sam deploy --guided

# 2回目以降
sam deploy
```

### テスト実行

```bash
# すべてのテストを実行
pytest tests/

# 単体テストのみ
pytest tests/unit/

# プロパティベーステストのみ
pytest tests/property/

# カバレッジ付き
pytest --cov=src --cov-report=html
```

## API エンドポイント

### メモ管理

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /memos | メモの作成 |
| GET | /memos | メモの一覧取得 |
| GET | /memos/{id} | メモの取得 |
| PUT | /memos/{id} | メモの更新 |
| DELETE | /memos/{id} | メモの削除 |

### AI機能

| メソッド | パス | 説明 |
|---------|------|------|
| POST | /memos/{id}/ask | 個別メモへのAI質問 |
| POST | /memos/summary | 全メモのAI要約生成 |

## 使用例

### メモの作成

```bash
curl -X POST https://api.example.com/memos \
  -H "Content-Type: application/json" \
  -d '{
    "title": "会議メモ",
    "content": "2024年1月15日の会議内容..."
  }'
```

### メモへのAI質問

```bash
curl -X POST https://api.example.com/memos/{memo_id}/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "この会議の主な決定事項は何ですか？"
  }'
```

### 全メモの要約生成

```bash
curl -X POST https://api.example.com/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}'
```

## アーキテクチャ概要

```
Client Application
       ↓
  API Gateway (REST API)
       ↓
   ┌───┴───┬────────┐
   ↓       ↓        ↓
Memo    AI      AllMemos
Function Function Summary
                Function
   ↓       ↓        ↓
   └───┬───┴────────┘
       ↓
   DynamoDB (MemoTable)
       
   AI Functions → AWS Bedrock
                  Claude Sonnet 4.6
                           
   All Functions → CloudWatch
```

### 主要コンポーネント

- **API Gateway**: RESTful APIエンドポイント、CORS有効
- **Memo Function**: メモCRUD操作（Python 3.13、10秒タイムアウト）
- **AI Function**: 個別メモAI質問（Python 3.13、35秒タイムアウト）
- **AllMemosSummary Function**: 全メモ要約（Python 3.13、65秒タイムアウト）
- **DynamoDB**: シングルテーブルデザイン、UpdatedAtIndex GSI
- **AWS Bedrock**: Claude Sonnet 4.6（Inference Profile経由）
- **CloudWatch**: ログとメトリクス

## 技術スタック

- **ランタイム**: Python 3.13
- **API**: Amazon API Gateway（REST API）
- **コンピュート**: AWS Lambda
- **データベース**: Amazon DynamoDB
- **AI**: AWS Bedrock Claude Sonnet 4.6
- **監視**: Amazon CloudWatch
- **IaC**: AWS SAM
- **SDK**: boto3、aws-lambda-powertools

## パフォーマンス目標

- メモCRUD操作: < 200ms（p95）
- メモ取得: < 100ms（p95）
- AI質問処理: < 30秒（p95）
- 全メモ要約生成: < 60秒（p95）

## セキュリティ

- IAMロールによる最小権限の原則
- 転送中の暗号化（HTTPS）
- 保存時の暗号化（DynamoDB SSE）
- API Gatewayリクエスト検証
- CORS設定

## 監視

### CloudWatchメトリクス

- リクエスト数
- エラー数
- 処理時間（p50、p95、p99）
- Lambda同時実行数

### CloudWatchアラーム

- エラー率 > 5%
- p95レイテンシ > しきい値
- Lambda同時実行数 > 80%

## コスト最適化

- Lambda: 適切なメモリ割り当て、コールドスタート最小化
- DynamoDB: オンデマンド価格設定、効率的なクエリパターン
- Bedrock: 効率的なプロンプト設計、インフェレンスプロファイル使用

## トラブルシューティング

### よくある問題

**1. Lambda タイムアウト**
- 原因: AI処理が長すぎる、DynamoDB接続遅延
- 解決: タイムアウト設定の確認、メモリ割り当ての増加

**2. DynamoDB スロットリング**
- 原因: 急激なトラフィック増加
- 解決: オンデマンド価格設定の確認、アクセスパターンの最適化

**3. Bedrock エラー**
- 原因: スロットリング、サービス利用不可
- 解決: リトライロジックの確認、リージョン設定の確認

### ログ確認

```bash
# Lambda関数のログを確認
aws logs tail /aws/lambda/MemoFunction --follow

# エラーログのフィルタリング
aws logs filter-log-events \
  --log-group-name /aws/lambda/AIFunction \
  --filter-pattern "ERROR"
```

## 今後の拡張

- 日付範囲によるフィルタリング機能
- メモのタグ付け機能
- ユーザー認証・認可（Amazon Cognito）
- メモの共有機能
- リアルタイム通知（WebSocket API）
- メモの全文検索（Amazon OpenSearch Service）

## ライセンス

このプロジェクトは社内利用のみを目的としています。

## サポート

質問や問題がある場合は、開発チームにお問い合わせください。

---

最終更新: 2024年1月
