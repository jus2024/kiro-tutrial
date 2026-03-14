---
name: deploy
description: SAMでビルド・デプロイを実行する
---
## 手順
1. `sam build` を実行してビルドする
2. `sam deploy --no-confirm-changeset` を実行してデプロイする
3. CloudFormation Outputs からAPI GatewayのURLを取得して表示する
4. デプロイ結果のサマリーを報告する