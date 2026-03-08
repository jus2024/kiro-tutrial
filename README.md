# AI要約API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![AWS SAM](https://img.shields.io/badge/AWS-SAM-orange.svg)](https://aws.amazon.com/serverless/sam/)

AWS上でサーバーレスに稼働するRESTful APIサービス。メモの作成・管理とAI（AWS Bedrock Claude）による質問応答・全メモ要約機能を提供します。

## 📋 目次

- [機能](#-機能)
- [アーキテクチャ](#-アーキテクチャ)
- [前提条件](#-前提条件)
- [セットアップ](#-セットアップ)
- [デプロイ](#-デプロイ)
- [API使用方法](#-api使用方法)
- [開発](#-開発)
- [テスト](#-テスト)
- [トラブルシューティング](#-トラブルシューティング)
- [ライセンス](#-ライセンス)

## ✨ 機能

- **メモ管理**: CRUD操作（作成・取得・更新・削除）
- **AI質問応答**: 個別メモの内容についてAIに質問
- **全メモ要約**: 全メモを対象にした包括的なAI要約生成
- **日本語対応**: UTF-8完全対応で日本語を含む多言語サポート
- **スケーラブル**: サーバーレスアーキテクチャによる自動スケーリング
- **監視**: CloudWatch Logs/Metricsによる包括的な監視

## 🏗 アーキテクチャ

- **Runtime**: Python 3.13
- **API**: Amazon API Gateway (REST API)
- **Compute**: AWS Lambda
- **Database**: Amazon DynamoDB (single-table design)
- **AI Service**: AWS Bedrock (Claude Sonnet 4.6)
- **IaC**: AWS SAM
- **Monitoring**: CloudWatch Logs & Metrics
- **Region**: us-west-2 (変更可能)

### アーキテクチャ図

```
┌─────────┐
│ Client  │
└────┬────┘
     │
     ▼
┌─────────────────┐
│  API Gateway    │
│  (REST API)     │
└────┬────────────┘
     │
     ├──────────────┬──────────────┬─────────────────┐
     ▼              ▼              ▼                 ▼
┌─────────┐   ┌─────────┐   ┌──────────────┐  ┌─────────────┐
│  Memo   │   │   AI    │   │  All Memos   │  │  CloudWatch │
│ Function│   │Function │   │   Summary    │  │ Logs/Metrics│
└────┬────┘   └────┬────┘   └──────┬───────┘  └─────────────┘
     │             │                │
     └─────────────┴────────────────┘
                   │
                   ▼
            ┌─────────────┐
            │  DynamoDB   │
            │ (MemoTable) │
            └─────────────┘
                   │
                   ▼
            ┌─────────────┐
            │AWS Bedrock  │
            │ Claude 4.6  │
            └─────────────┘
```

## プロジェクト構成

```
.
├── src/
│   ├── functions/          # Lambda関数ハンドラー
│   │   ├── memo/          # メモCRUD操作
│   │   ├── ai/            # AI質問応答
│   │   └── all_memos_summary/  # 全メモ要約
│   ├── models/            # データモデル
│   ├── repositories/      # データアクセス層
│   ├── services/          # ビジネスロジック
│   └── utils/             # ユーティリティ関数
├── tests/
│   ├── unit/              # ユニットテスト
│   ├── property/          # プロパティベーステスト
│   └── integration/       # 統合テスト
├── events/                # テスト用イベントペイロード
├── .kiro/specs/           # 機能仕様書
│   └── all-memos-summary/ # 全メモ要約機能の詳細ドキュメント
├── template.yaml          # SAMテンプレート
├── samconfig.toml         # SAM設定
└── requirements.txt       # Python依存関係
```

## 📋 前提条件

### 必須ツール

以下のツールがインストールされている必要があります：

#### 1. Python 3.13以上

```bash
# バージョン確認
python3 --version

# インストール（macOS - Homebrew）
brew install python@3.13

# インストール（Ubuntu/Debian）
sudo apt update
sudo apt install python3.13 python3.13-venv python3-pip

# インストール（Windows）
# https://www.python.org/downloads/ からインストーラーをダウンロード
```

#### 2. AWS CLI

```bash
# バージョン確認
aws --version

# インストール（macOS - Homebrew）
brew install awscli

# インストール（Linux）
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# インストール（Windows）
# https://aws.amazon.com/cli/ からインストーラーをダウンロード

# AWS認証情報の設定
aws configure
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY
# Default region name: us-west-2
# Default output format: json
```

#### 3. AWS SAM CLI

```bash
# バージョン確認
sam --version

# インストール（macOS - Homebrew）
brew install aws-sam-cli

# インストール（Linux）
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html

# インストール（Windows）
# https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

#### 4. Docker Desktop（ローカルテスト用・オプション）

SAM Localを使用する場合に必要です。

```bash
# インストール
# https://www.docker.com/products/docker-desktop からダウンロード
```

### AWS アカウント設定

#### 1. IAM権限

デプロイを実行するIAMユーザー/ロールには以下の権限が必要です：

- `AWSCloudFormationFullAccess`
- `IAMFullAccess`
- `AWSLambda_FullAccess`
- `AmazonDynamoDBFullAccess`
- `AmazonAPIGatewayAdministrator`
- `CloudWatchLogsFullAccess`

#### 2. AWS Bedrock モデルアクセスの有効化

**重要**: AWS Bedrockで Claude Sonnet 4.6 を使用するには、事前にモデルアクセスを有効化する必要があります。

1. AWS Management Consoleにログイン
2. **us-west-2 (オレゴン)** リージョンに切り替え
3. **Amazon Bedrock** サービスに移動
4. 左メニューから **Model access** を選択
5. **Manage model access** をクリック
6. **Anthropic** セクションで **Claude 3.5 Sonnet v2** と **Claude Sonnet 4** にチェック
7. **Request model access** をクリック

> **注意**: モデルアクセスの承認には数分かかる場合があります。承認されるまで待ってからデプロイしてください。

#### 3. リージョンの選択

このプロジェクトはデフォルトで **us-west-2 (オレゴン)** を使用します。他のリージョンを使用する場合：

- Bedrockが利用可能なリージョンか確認してください
- `samconfig.toml` の `region` パラメータを変更してください
- `template.yaml` の `BEDROCK_REGION` 環境変数を変更してください

Bedrock利用可能リージョン: us-east-1, us-west-2, ap-northeast-1, eu-central-1 など
（最新情報は[AWS公式ドキュメント](https://docs.aws.amazon.com/bedrock/latest/userguide/what-is-bedrock.html)を参照）

## セットアップとデプロイ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. ビルド

```bash
sam build
```

### 3. AWSへデプロイ

初回デプロイ（対話形式で設定）:

```bash
sam deploy --guided
```

対話で以下を設定:
- Stack Name: `ai-memo-api`（任意の名前）
- AWS Region: `us-west-2`（推奨）
- Confirm changes before deploy: `y`
- Allow SAM CLI IAM role creation: `y`
- Disable rollback: `n`
- Save arguments to configuration file: `y`

2回目以降のデプロイ:

```bash
sam build && sam deploy
```

環境を指定してデプロイ:

```bash
sam deploy --parameter-overrides Environment=staging
```

### 4. ローカルテスト（オプション）

Docker Desktopが必要です。インストール後:

```bash
# API Gatewayをローカルで起動
sam local start-api

# 特定のLambda関数を実行
sam local invoke MemoFunction -e events/create_memo.json
```

## API エンドポイント

デプロイ後、以下のようなURLが出力されます:
```
https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev
```

### メモ操作

- `POST /memos` - メモ作成
- `GET /memos/{id}` - メモ取得
- `GET /memos` - メモ一覧取得（ページネーション対応）
- `PUT /memos/{id}` - メモ更新
- `DELETE /memos/{id}` - メモ削除

### AI質問

- `POST /memos/{id}/ask` - メモ内容についてAIに質問

### 全メモ要約

- `POST /memos/summary` - 全メモの包括的な要約を生成

### 使用例

```bash
# API URLを環境変数に設定（デプロイ時の出力から取得）
export API_URL="https://xxxxxxxxxx.execute-api.us-west-2.amazonaws.com/dev"

# メモ作成
curl -X POST $API_URL/memos \
  -H "Content-Type: application/json" \
  -d '{"title":"テストメモ","content":"これはテスト用のメモです"}'

# メモ一覧取得
curl $API_URL/memos

# AI質問（memo_idは作成時に取得したIDを使用）
curl -X POST $API_URL/memos/{memo_id}/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"このメモの内容を要約してください"}'

# 全メモ要約生成
curl -X POST $API_URL/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}'

# 全メモ要約を見やすく整形して表示
curl -X POST $API_URL/memos/summary \
  -H "Content-Type: application/json" \
  -d '{}' | python3 scripts/format_summary.py
```

#### レスポンス例

**全メモ要約のレスポンス:**
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

**空のメモコレクションの場合:**
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

## 🧪 テスト

このプロジェクトは包括的なテストスイートを含んでいます：

- **ユニットテスト**: 60+ テスト
- **プロパティベーステスト**: 7つのプロパティ × 100イテレーション
- **統合テスト**: エンドツーエンドのAPIテスト

### テスト環境のセットアップ

```bash
# テスト用依存関係のインストール
pip install -r requirements.txt

# pytest, hypothesis, moto などがインストールされます
```

### ユニットテスト実行

```bash
pytest tests/unit/ -v
```

### プロパティベーステスト実行

プロパティベーステストは[Hypothesis](https://hypothesis.readthedocs.io/)を使用して、各プロパティを100回以上のランダムな入力でテストします。

```bash
pytest tests/property/ -v
```

### 全テスト実行（カバレッジ付き）

```bash
pytest --cov=src tests/

# HTMLレポート生成
pytest --cov=src --cov-report=html tests/
# htmlcov/index.html をブラウザで開く
```

### テスト例

```bash
# 特定のテストファイルのみ実行
pytest tests/unit/test_memo_aggregator.py -v

# 特定のテストケースのみ実行
pytest tests/unit/test_memo_aggregator.py::test_aggregate_memos_basic -v

# 失敗したテストのみ再実行
pytest --lf

# 詳細な出力
pytest -vv -s
```

## ユーティリティスクリプト

### 要約結果の整形表示

`scripts/format_summary.py` を使用すると、全メモ要約のレスポンスを見やすく整形して表示できます。

```bash
# パイプで直接整形
curl -X POST $API_URL/memos/summary -d '{}' | python3 scripts/format_summary.py

# ファイルから読み込んで整形
python3 scripts/format_summary.py response.json

# ヘルプ表示
python3 scripts/format_summary.py --help
```

出力例:
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

あなたのメモには主に3つのテーマがあります：1) プロジェクト管理...

================================================================================
```

## 💻 開発

### 開発環境のセットアップ

```bash
# リポジトリのクローン
git clone https://github.com/YOUR_USERNAME/ai-memo-api.git
cd ai-memo-api

# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 開発用依存関係のインストール（オプション）
pip install black flake8 mypy
```

### コード品質ツール

#### コードフォーマット

```bash
# Blackでコードを自動整形
black src/ tests/

# 確認のみ（変更なし）
black --check src/ tests/
```

#### リント

```bash
# Flake8でコードスタイルをチェック
flake8 src/ tests/

# 特定のルールを無視
flake8 src/ tests/ --ignore=E501,W503
```

#### 型チェック

```bash
# Mypyで型ヒントをチェック
mypy src/
```

### ローカル開発ワークフロー

1. **コード変更**
2. **フォーマット**: `black src/ tests/`
3. **リント**: `flake8 src/ tests/`
4. **型チェック**: `mypy src/`
5. **テスト**: `pytest tests/`
6. **ビルド**: `sam build`
7. **ローカルテスト**: `sam local start-api`
8. **デプロイ**: `sam deploy`

### Git ワークフロー

```bash
# 新しいブランチを作成
git checkout -b feature/new-feature

# 変更をコミット
git add .
git commit -m "feat: add new feature"

# プッシュ
git push origin feature/new-feature

# プルリクエストを作成
```

## 環境変数

Lambda関数で使用される環境変数:

### Memo Function
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `LOG_LEVEL`: ログレベル（INFO）
- `POWERTOOLS_SERVICE_NAME`: サービス名

### AI Function
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `BEDROCK_MODEL_ID`: Claudeモデル識別子（デフォルト: `us.anthropic.claude-sonnet-4-6`）
- `BEDROCK_REGION`: Bedrockリージョン（us-west-2）
- `MAX_RETRIES`: リトライ回数（3）
- `LOG_LEVEL`: ログレベル（INFO）
- `POWERTOOLS_SERVICE_NAME`: サービス名

### All Memos Summary Function
- `MEMO_TABLE_NAME`: DynamoDBテーブル名
- `BEDROCK_MODEL_ID`: Claudeモデル識別子（デフォルト: `us.anthropic.claude-sonnet-4-6`）
- `BEDROCK_REGION`: Bedrockリージョン（us-west-2）
- `MAX_RETRIES`: リトライ回数（3）
- `MAX_CONTENT_TOKENS`: AI処理の最大トークン数（180000）
- `LOG_LEVEL`: ログレベル（INFO）
- `POWERTOOLS_SERVICE_NAME`: サービス名

## モニタリング

CloudWatch Logsでログを確認:

```bash
sam logs -n MemoFunction --tail
sam logs -n AIFunction --tail
sam logs -n AllMemosSummaryFunction --tail
```

## 機能詳細

### 全メモ要約機能

全メモ要約機能は、システムに保存されている全てのメモを対象にAI（AWS Bedrock Claude Sonnet 4.6）による包括的な要約を生成します。

**特徴:**
- 最大180,000トークン（約720,000文字）のコンテンツを処理
- コンテンツ制限を超える場合、最新のメモを優先的に選択
- エクスポネンシャルバックオフによる自動リトライ（1秒、2秒、4秒）
- 構造化ログとCloudWatchメトリクスによる監視
- 処理時間: 通常2-5秒、大量メモで5-15秒

**詳細なドキュメント:**
全メモ要約機能の詳細な使い方、トラブルシューティング、パフォーマンス情報については、[全メモ要約機能README](.kiro/specs/all-memos-summary/README.md)を参照してください。

## � コスト見積もり

このアプリケーションは従量課金制のサーバーレスアーキテクチャを使用しています。

### 月間コスト例（us-west-2リージョン）

**想定利用量**:
- API呼び出し: 10,000回/月
- メモ数: 100件
- 全メモ要約: 100回/月

| サービス | 使用量 | 月額コスト（USD） |
|---------|--------|------------------|
| API Gateway | 10,000リクエスト | $0.04 |
| Lambda（実行時間） | 10,000回 × 1秒 × 256MB | $0.03 |
| Lambda（リクエスト） | 10,000回 | $0.002 |
| DynamoDB（オンデマンド） | 10,000読み取り + 1,000書き込み | $0.03 |
| Bedrock Claude Sonnet 4.6 | 100回 × 50K入力 + 2K出力トークン | $1.50 |
| CloudWatch Logs | 1GB | $0.50 |
| **合計** | | **約 $2.10/月** |

### コスト最適化のヒント

1. **DynamoDB**: オンデマンドモードを使用（予測可能な負荷の場合はプロビジョニングモードも検討）
2. **Lambda**: 適切なメモリサイズを設定（過剰なメモリは無駄）
3. **CloudWatch Logs**: ログ保持期間を設定（デフォルトは無期限）
4. **Bedrock**: 不要な要約生成を避ける、プロンプトを最適化してトークン数を削減

### 無料利用枠

AWS無料利用枠（12ヶ月間）:
- Lambda: 100万リクエスト/月、400,000 GB-秒/月
- DynamoDB: 25GB ストレージ、25読み取り/書き込みキャパシティユニット
- API Gateway: 100万API呼び出し/月（12ヶ月間）

> **注意**: Bedrockには無料利用枠がありません。使用した分だけ課金されます。

### コスト監視

```bash
# AWS Cost Explorerでコストを確認
# AWS Console → Cost Management → Cost Explorer

# 予算アラートの設定を推奨
# AWS Console → Billing → Budgets
```

## 🔧 トラブルシューティング

### デプロイ時の問題

#### 1. CloudFormation スタックの作成に失敗

**症状**: `CREATE_FAILED` エラー

**原因と対処**:
- IAM権限不足 → IAMユーザーに必要な権限を付与
- リソース名の重複 → スタック名を変更して再デプロイ
- リージョンの制限 → 別のリージョンを試す

```bash
# スタックの削除
sam delete

# 再デプロイ
sam deploy --guided
```

#### 2. Bedrock モデルアクセスエラー

**症状**: `AccessDeniedException` または `ValidationException`

**原因**: Bedrockモデルへのアクセスが有効化されていない

**対処**:
1. AWS Consoleで **us-west-2** リージョンに切り替え
2. Amazon Bedrock → Model access
3. Claude Sonnet 4.6 を有効化
4. 承認を待つ（数分）
5. 再度APIを実行

#### 3. Lambda タイムアウトエラー

**症状**: `Task timed out after X seconds`

**原因**: 大量のメモ処理やBedrock APIの遅延

**対処**:
```yaml
# template.yaml で Timeout を増やす
AllMemosSummaryFunction:
  Properties:
    Timeout: 60  # デフォルト30秒 → 60秒に変更
```

### API実行時の問題

#### 1. 500 Internal Server Error

**症状**: API呼び出しで500エラー

**デバッグ手順**:
```bash
# CloudWatch Logsを確認
sam logs -n AllMemosSummaryFunction --tail

# 最近のエラーを検索
aws logs filter-log-events \
  --log-group-name /aws/lambda/AllMemosSummaryFunction \
  --filter-pattern "ERROR"
```

**よくある原因**:
- DynamoDBテーブルが存在しない → デプロイを確認
- Bedrock APIエラー → モデルアクセスを確認
- メモリ不足 → Lambda メモリサイズを増やす

#### 2. No module named 'src' エラー

**症状**: Lambda実行時に `ModuleNotFoundError: No module named 'src'`

**原因**: Lambda環境では `src.` プレフィックスが不要

**対処**:
```python
# ❌ 間違い
from src.models.summary_models import AggregationResult

# ✅ 正しい
from models.summary_models import AggregationResult
```

#### 3. 文字化け（日本語が正しく表示されない）

**症状**: レスポンスの日本語が文字化け

**原因**: UTF-8エンコーディングの問題

**対処**: すでに実装済み（Content-Type: application/json; charset=utf-8）

### ローカルテスト時の問題

#### 1. Docker が起動していない

**症状**: `sam local` コマンドでエラー

**対処**:
```bash
# Docker Desktop を起動
# macOS: アプリケーションから起動
# Linux: sudo systemctl start docker
# Windows: Docker Desktop を起動

# Docker が動作しているか確認
docker ps
```

#### 2. ポートが既に使用されている

**症状**: `Address already in use`

**対処**:
```bash
# 使用中のポートを確認
lsof -i :3000

# プロセスを終了
kill -9 <PID>

# 別のポートを使用
sam local start-api --port 3001
```

### パフォーマンスの問題

#### 1. 全メモ要約が遅い

**症状**: 処理時間が15秒以上

**原因**: 大量のメモ（100件以上）

**対処**:
- メモの数を減らす
- `MAX_CONTENT_TOKENS` を調整（デフォルト: 180000）
- Lambda メモリサイズを増やす（処理速度向上）

```yaml
# template.yaml
AllMemosSummaryFunction:
  Properties:
    MemorySize: 512  # デフォルト256 → 512に増やす
```

### その他の問題

#### AWS認証情報エラー

```bash
# 認証情報を再設定
aws configure

# 認証情報を確認
aws sts get-caller-identity
```

#### SAM ビルドエラー

```bash
# キャッシュをクリア
rm -rf .aws-sam/

# 再ビルド
sam build --use-container
```

### サポート

問題が解決しない場合:
1. [GitHub Issues](https://github.com/YOUR_USERNAME/ai-memo-api/issues) で既存の問題を検索
2. 新しいIssueを作成（エラーメッセージとログを含める）
3. [AWS Bedrock ドキュメント](https://docs.aws.amazon.com/bedrock/)を参照

スタックを削除:

```bash
sam delete
```

## 🤝 コントリビューション

コントリビューションを歓迎します！以下の方法で貢献できます：

### バグ報告

バグを見つけた場合は、[GitHub Issues](https://github.com/YOUR_USERNAME/ai-memo-api/issues)で報告してください。

報告時に含めるべき情報:
- バグの説明
- 再現手順
- 期待される動作
- 実際の動作
- エラーメッセージ（あれば）
- 環境情報（OS、Python バージョン、AWS リージョンなど）

### 機能リクエスト

新機能のアイデアがある場合は、Issueで提案してください。

### プルリクエスト

1. このリポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

#### プルリクエストのガイドライン

- コードは `black` でフォーマットする
- `flake8` と `mypy` のチェックをパスする
- 新機能には必ずテストを追加する
- コミットメッセージは [Conventional Commits](https://www.conventionalcommits.org/) に従う
  - `feat:` 新機能
  - `fix:` バグ修正
  - `docs:` ドキュメント変更
  - `test:` テスト追加・修正
  - `refactor:` リファクタリング

### 開発環境のセットアップ

```bash
# フォークしたリポジトリをクローン
git clone https://github.com/YOUR_USERNAME/ai-memo-api.git
cd ai-memo-api

# 仮想環境を作成
python3 -m venv venv
source venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt
pip install black flake8 mypy

# テストを実行
pytest tests/

# コード品質チェック
black src/ tests/
flake8 src/ tests/
mypy src/
```

## 📄 ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。詳細は [LICENSE](LICENSE) ファイルを参照してください。

## 🙏 謝辞

このプロジェクトは以下のオープンソースプロジェクトを使用しています：

- [AWS SAM](https://aws.amazon.com/serverless/sam/) - サーバーレスアプリケーションフレームワーク
- [AWS Lambda Powertools](https://awslabs.github.io/aws-lambda-powertools-python/) - Lambda ユーティリティ
- [Hypothesis](https://hypothesis.readthedocs.io/) - プロパティベーステストフレームワーク
- [pytest](https://pytest.org/) - テストフレームワーク

## 📞 連絡先

質問や提案がある場合:
- GitHub Issues: [https://github.com/YOUR_USERNAME/ai-memo-api/issues](https://github.com/YOUR_USERNAME/ai-memo-api/issues)
- Email: your.email@example.com

---

⭐ このプロジェクトが役に立った場合は、GitHubでスターをつけてください！
