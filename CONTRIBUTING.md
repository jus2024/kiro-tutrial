# コントリビューションガイド

AI Memo API プロジェクトへのコントリビューションに興味を持っていただき、ありがとうございます！

## 行動規範

このプロジェクトに参加するすべての人は、敬意を持って協力的な態度で接することが期待されます。

## コントリビューションの方法

### バグ報告

バグを見つけた場合は、以下の情報を含めて [GitHub Issues](https://github.com/YOUR_USERNAME/ai-memo-api/issues) で報告してください：

- **明確なタイトル**: バグの内容を簡潔に説明
- **再現手順**: バグを再現するための詳細な手順
- **期待される動作**: 本来どのように動作すべきか
- **実際の動作**: 実際にどのように動作したか
- **エラーメッセージ**: 該当する場合、完全なエラーメッセージとスタックトレース
- **環境情報**:
  - OS（macOS、Linux、Windows）
  - Python バージョン
  - AWS リージョン
  - SAM CLI バージョン

### 機能リクエスト

新機能のアイデアがある場合は、Issue で提案してください：

- **ユースケース**: なぜこの機能が必要か
- **提案する実装**: 可能であれば、実装方法のアイデア
- **代替案**: 検討した他のアプローチ

### プルリクエスト

#### 開発環境のセットアップ

```bash
# 1. リポジトリをフォーク
# GitHubのWebインターフェースで "Fork" ボタンをクリック

# 2. フォークしたリポジトリをクローン
git clone https://github.com/YOUR_USERNAME/ai-memo-api.git
cd ai-memo-api

# 3. 仮想環境を作成して有効化
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 4. 依存関係をインストール
pip install -r requirements.txt

# 5. 開発用ツールをインストール
pip install black flake8 mypy pytest-cov

# 6. テストが通ることを確認
pytest tests/
```

#### ブランチ戦略

```bash
# 新しいブランチを作成
git checkout -b feature/your-feature-name
# または
git checkout -b fix/your-bug-fix
```

ブランチ名の規則:
- `feature/` - 新機能
- `fix/` - バグ修正
- `docs/` - ドキュメント変更
- `test/` - テスト追加・修正
- `refactor/` - リファクタリング

#### コーディング規約

1. **コードスタイル**
   - [PEP 8](https://pep8.org/) に従う
   - `black` でコードをフォーマット
   - 行の長さは最大88文字（black のデフォルト）

2. **型ヒント**
   - すべての関数に型ヒントを追加
   - `mypy` でチェック

3. **ドキュメント**
   - すべての public 関数に docstring を追加
   - Google スタイルの docstring を使用

4. **テスト**
   - 新機能には必ずテストを追加
   - バグ修正には再現テストを追加
   - テストカバレッジを維持（80%以上）

#### コード品質チェック

プルリクエストを作成する前に、以下のチェックを実行してください：

```bash
# コードフォーマット
black src/ tests/

# リント
flake8 src/ tests/

# 型チェック
mypy src/

# テスト実行
pytest tests/ -v

# カバレッジチェック
pytest --cov=src --cov-report=term-missing tests/
```

#### コミットメッセージ

[Conventional Commits](https://www.conventionalcommits.org/) 形式を使用してください：

```
<type>: <subject>

<body>

<footer>
```

**Type**:
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメント変更
- `style`: コードスタイル変更（機能に影響なし）
- `refactor`: リファクタリング
- `test`: テスト追加・修正
- `chore`: ビルドプロセスやツールの変更

**例**:
```
feat: add pagination support to memo list API

- Add limit and next_token parameters
- Update DynamoDB query to support pagination
- Add tests for pagination logic

Closes #123
```

#### プルリクエストの作成

1. 変更をコミット
```bash
git add .
git commit -m "feat: add your feature"
```

2. フォークにプッシュ
```bash
git push origin feature/your-feature-name
```

3. GitHub でプルリクエストを作成
   - 明確なタイトルと説明を記載
   - 関連する Issue を参照（`Closes #123`）
   - スクリーンショットやログを含める（該当する場合）

4. レビューを待つ
   - レビュアーからのフィードバックに対応
   - 必要に応じて変更を追加コミット

## プルリクエストのチェックリスト

プルリクエストを作成する前に、以下を確認してください：

- [ ] コードが `black` でフォーマットされている
- [ ] `flake8` のチェックをパスしている
- [ ] `mypy` の型チェックをパスしている
- [ ] すべてのテストがパスしている
- [ ] 新機能にはテストが追加されている
- [ ] ドキュメントが更新されている（必要な場合）
- [ ] コミットメッセージが Conventional Commits に従っている
- [ ] CHANGELOG.md が更新されている（重要な変更の場合）

## テストの書き方

### ユニットテスト

```python
import pytest
from services.memo_aggregator import MemoAggregator

def test_aggregate_memos_basic():
    """Test basic memo aggregation functionality."""
    aggregator = MemoAggregator(max_tokens=1000)
    memos = [
        {"memo_id": "1", "content": "Test memo 1"},
        {"memo_id": "2", "content": "Test memo 2"},
    ]
    
    result = aggregator.aggregate_memos(memos)
    
    assert result.total_memos == 2
    assert len(result.included_memos) == 2
```

### プロパティベーステスト

```python
from hypothesis import given, strategies as st
from services.memo_aggregator import MemoAggregator

@given(st.lists(st.text(min_size=1, max_size=100), min_size=0, max_size=50))
def test_aggregator_handles_any_content(contents):
    """Property: aggregator should handle any list of text content."""
    aggregator = MemoAggregator(max_tokens=10000)
    memos = [{"memo_id": str(i), "content": c} for i, c in enumerate(contents)]
    
    result = aggregator.aggregate_memos(memos)
    
    assert result.total_memos == len(memos)
    assert len(result.included_memos) <= len(memos)
```

## ドキュメントの更新

コードの変更に伴い、以下のドキュメントを更新してください：

- `README.md` - API の変更、新機能の追加
- `.kiro/specs/*/README.md` - 機能固有のドキュメント
- Docstrings - 関数やクラスの説明

## リリースプロセス

メンテナーのみが実行します：

1. バージョン番号を更新（[Semantic Versioning](https://semver.org/)）
2. CHANGELOG.md を更新
3. Git タグを作成
4. GitHub Release を作成

## 質問がある場合

- GitHub Issues で質問を投稿
- 既存の Issue やプルリクエストを検索
- README.md のドキュメントを確認

## ライセンス

このプロジェクトに貢献することで、あなたのコントリビューションが MIT ライセンスの下でライセンスされることに同意したものとみなされます。
