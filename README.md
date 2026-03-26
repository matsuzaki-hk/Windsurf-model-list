# Windsurf Model List

Windsurfのモデルリストを自動取得するPythonスクリプトです。

## 機能

- [Windsurf Modelsページ](https://docs.windsurf.com/windsurf/models) から自動的にモデル情報を取得
- **3コスト項目対応**: 入力コスト、キャッシュ入力コスト、出力コストを個別に取得
- **タブ別取得**: Self-serve配下の各タブ（Recommended、Windsurf、Anthropic、OpenAI、Google）から個別に取得
- **重複排除**: Markdown出力時にモデル名で重複を排除
- **日本語表記**: Markdownテーブルのヘッダーを日本語で表示

## 取得データ形式

### JSON形式 (`models_output.json`)
```json
{
  "Recommended": [
    {
      "model": "Claude Sonnet 4.5",
      "input_cost": "$3.00",
      "cache_input_cost": "$0.30",
      "output_cost": "$15.00"
    }
  ]
}
```

### Markdown形式 (`models_table.md`)
| モデル名 | 入力 (100万トークン) | キャッシュ入力 (100万トークン) | 出力 (100万トークン) |
|---------|---------------------|---------------------------|---------------------|
| Claude Sonnet 4.5 | $3.00 | $0.30 | $15.00 |

## 使用方法

### 必要条件
- Python 3.7以上
- Playwright (`pip install playwright`)
- Chromium (`playwright install chromium`)

### インストール
```bash
pip install playwright
playwright install chromium
```

### 実行
```bash
# Pythonスクリプトで実行
python fetch_models.py

# またはバッチファイルで実行
fetch_models.bat
```

### 出力ファイル
- `models_output.json` - 生データ（JSON形式）
- `models_table.md` - 整形済みモデル一覧（Markdown形式）

## 取得されるモデル一覧

| タブ | 取得モデル数（例） |
|------|------------------|
| Recommended | 8 |
| Windsurf | 6 |
| Anthropic | 18 |
| OpenAI | 66 |
| Google | 9 |

## 技術的特徴

### データ取得方法
- **動的タブ検出**: `.cost-tab-button`クラスを優先的に使用してサブタブを動的に検出
- **価格フィルタリング**: 価格表記（$または—）によるフィルタリングで正確なデータを取得
- **フォールバック**: JavaScript実行エラー時には従来の方法でデータ取得

### コスト計算基準
- **Input**: 入力トークン100万個あたりのコスト
- **Cache Input**: キャッシュされた入力トークン100万個あたりのコスト
- **Output**: 出力トークン100万個あたりのコスト

## 更新履歴

- 2026/03/26: 3コスト項目対応、日本語表記、重複排除機能を追加

## ライセンス

MIT License
