# Claude Skills 使用ガイド

**作成日**: 2025年10月20日
**対象**: BSF-LoopTech プロジェクト

---

## 📚 Claude Skillsとは？

**Claude Skills**は、Claude Codeに専門知識やワークフローを追加できる機能です（2025年10月16日正式リリース）。

### 特徴
- スキルは `~/.claude/skills/` ディレクトリに配置
- `SKILL.md` ファイルで定義された手順・知識をClaude が自動的に読み込み
- タスクに応じて関連するスキルを自動選択・実行
- スクリプト、リファレンス、アセットなどのリソースをバンドル可能

---

## 🎯 インストール済みスキル一覧

### 1. **skill-creator**
**説明**: 新しいスキルを作成するための対話的ガイド
**用途**: カスタムスキルの作成・編集・パッケージング
**場所**: `~/.claude/skills/skill-creator/`

**主な機能**:
- スキル作成プロセスのステップバイステップガイド
- スキル初期化スクリプト (`scripts/init_skill.py`)
- スキルパッケージング (`scripts/package_skill.py`)
- ベストプラクティスの提供

**使い方**:
```bash
# 新しいスキルを作成
~/.claude/skills/skill-creator/scripts/init_skill.py my-new-skill --path ~/.claude/skills

# スキルをパッケージ化
~/.claude/skills/skill-creator/scripts/package_skill.py ~/.claude/skills/my-skill
```

---

### 2. **document-skills** (4つのサブスキル)

#### 2.1 **docx** - Word文書操作
**説明**: Word文書の作成・編集・分析
**場所**: `~/.claude/skills/document-skills/docx/`

**主な機能**:
- 変更履歴とコメントのサポート
- 書式保持
- テキスト抽出

#### 2.2 **pdf** - PDF操作
**説明**: PDFの包括的な操作ツールキット
**場所**: `~/.claude/skills/document-skills/pdf/`

**主な機能**:
- テキスト・テーブル抽出
- 新規PDF作成
- 結合・分割
- フォーム処理

#### 2.3 **xlsx** - Excel操作
**説明**: Excelファイルの作成・編集・分析
**場所**: `~/.claude/skills/document-skills/xlsx/`

**主な機能**:
- データ分析
- グラフ作成
- 数式処理

#### 2.4 **pptx** - PowerPoint操作
**説明**: PowerPointプレゼンテーションの作成・編集
**場所**: `~/.claude/skills/document-skills/pptx/`

**主な機能**:
- スライド作成
- レイアウト調整
- 画像・グラフ挿入

---

### 3. **artifacts-builder**
**説明**: 複雑なフロントエンドアーティファクト作成ツール
**場所**: `~/.claude/skills/artifacts-builder/`

**技術スタック**:
- React 18 + TypeScript
- Vite + Parcel（バンドリング）
- Tailwind CSS
- shadcn/ui（40+コンポーネント）

**主な機能**:
- React プロジェクトの初期化
- 単一HTMLファイルへのバンドル
- shadcn/ui コンポーネントの統合

**使い方**:
```bash
# プロジェクト初期化
bash ~/.claude/skills/artifacts-builder/scripts/init-artifact.sh my-app
cd my-app

# 開発後、単一HTMLファイルにバンドル
bash ~/.claude/skills/artifacts-builder/scripts/bundle-artifact.sh
```

**デザインガイドライン**:
- ❌ 避けるべき: 過度な中央揃え、紫のグラデーション、画一的な丸角、Interフォント
- ✅ 推奨: モダンで洗練されたデザイン

---

## 🚀 スキルの使い方

### 基本的な使い方

Claude Codeでは、スキルを**明示的に呼び出す必要はありません**。Claude が自動的に関連するスキルを検出して使用します。

**例**:
```
「このPDFからテキストを抽出して」
→ pdf スキルが自動的に使用される

「React でダッシュボードを作って」
→ artifacts-builder スキルが自動的に使用される

「新しいスキルを作りたい」
→ skill-creator スキルが自動的に使用される
```

### 明示的にスキルを使用する場合

Skillツールを使って明示的にスキルを呼び出すこともできます：

```
/skill-creator
/pdf
/docx
```

---

## 📁 スキルの構造

### 標準的なスキル構造
```
skill-name/
├── SKILL.md (必須)
│   ├── YAML frontmatter メタデータ (必須)
│   │   ├── name: (必須)
│   │   └── description: (必須)
│   └── Markdown 手順書 (必須)
└── バンドルリソース (オプション)
    ├── scripts/          - 実行可能コード (Python/Bash等)
    ├── references/       - 必要に応じて読み込むドキュメント
    └── assets/           - 出力で使用するファイル (テンプレート等)
```

### SKILL.md の例
```markdown
---
name: my-skill
description: このスキルは〇〇を行うときに使用される
license: Complete terms in LICENSE.txt
---

# My Skill

## 目的
このスキルの目的を数文で説明

## いつ使うか
- ユーザーが〇〇を要求したとき
- △△の処理が必要なとき

## 使い方
1. 最初に××を実行
2. 次に□□を確認
3. 最後に◇◇を出力
```

---

## 🛠️ カスタムスキルの作成

### ステップ1: スキルの初期化

```bash
# skill-creator のスクリプトを使用
~/.claude/skills/skill-creator/scripts/init_skill.py my-custom-skill --path ~/.claude/skills
```

これにより以下が自動生成されます：
- `SKILL.md` テンプレート（YAML frontmatter付き）
- `scripts/` ディレクトリ（サンプルスクリプト付き）
- `references/` ディレクトリ
- `assets/` ディレクトリ

### ステップ2: SKILL.md の編集

```markdown
---
name: bsf-data-analyzer
description: BSF養殖データの分析と可視化を行うスキル。センサーデータと基質データの相関分析に使用
license: MIT
---

# BSF Data Analyzer

## 目的
BSF-LoopTechプロジェクトのセンサーデータと基質データを分析し、養殖効率を最適化する。

## いつ使うか
- センサーデータの統計分析が必要なとき
- 基質配合と成長率の相関分析を行うとき
- 異常値検出が必要なとき

## 使い方
1. InfluxDBからセンサーデータを取得
2. PostgreSQLから基質データを取得
3. pandas で相関分析を実行
4. matplotlib/plotly でグラフ作成
5. 分析結果をレポート形式で出力
```

### ステップ3: スクリプトの追加（オプション）

```bash
# scripts/analyze_correlation.py を作成
cat > ~/.claude/skills/bsf-data-analyzer/scripts/analyze_correlation.py << 'EOF'
#!/usr/bin/env python3
import pandas as pd
import matplotlib.pyplot as plt

def analyze_substrate_sensor_correlation(substrate_data, sensor_data):
    """基質データとセンサーデータの相関分析"""
    # データ結合
    merged = pd.merge(substrate_data, sensor_data, on='timestamp')

    # 相関係数計算
    correlation = merged.corr()

    # ヒートマップ作成
    plt.figure(figsize=(10, 8))
    plt.imshow(correlation, cmap='coolwarm')
    plt.colorbar()
    plt.title('Substrate-Sensor Correlation Heatmap')
    plt.savefig('correlation_heatmap.png')

    return correlation

if __name__ == "__main__":
    # テスト実行
    pass
EOF

chmod +x ~/.claude/skills/bsf-data-analyzer/scripts/analyze_correlation.py
```

### ステップ4: パッケージング

```bash
# スキルをzipファイルにパッケージ化
~/.claude/skills/skill-creator/scripts/package_skill.py ~/.claude/skills/bsf-data-analyzer
```

---

## 📊 BSF-LoopTechプロジェクトでの活用例

### 1. 見積書・仕様書の作成
**使用スキル**: docx, pdf

```
「見積依頼仕様書をWord文書として整形して」
→ docx スキルが使用され、適切なフォーマットでWord文書を生成
```

### 2. データ分析レポート
**使用スキル**: xlsx, pdf

```
「センサーデータの統計分析結果をExcelにまとめて」
→ xlsx スキルが使用され、グラフ付きExcelファイルを生成
```

### 3. プレゼンテーション資料
**使用スキル**: pptx

```
「補助金申請用のプレゼン資料を作成して」
→ pptx スキルが使用され、PowerPointプレゼンテーションを生成
```

### 4. ダッシュボード開発
**使用スキル**: artifacts-builder

```
「BSFセンサーデータのリアルタイムダッシュボードを作って」
→ artifacts-builder スキルが使用され、React ダッシュボードを生成
```

---

## 🔧 トラブルシューティング

### スキルが認識されない

**確認事項**:
1. スキルが `~/.claude/skills/` に正しく配置されているか
2. `SKILL.md` ファイルが存在するか
3. YAML frontmatter が正しい形式か（name と description が必須）

```bash
# スキル一覧を確認
ls -la ~/.claude/skills/

# SKILL.md の存在確認
find ~/.claude/skills -name "SKILL.md"
```

### スクリプトが実行されない

**確認事項**:
1. スクリプトに実行権限があるか
2. shebang（`#!/usr/bin/env python3` など）が正しいか
3. 依存パッケージがインストールされているか

```bash
# 実行権限を付与
chmod +x ~/.claude/skills/my-skill/scripts/my-script.py

# 依存パッケージのインストール
pip install -r ~/.claude/skills/my-skill/requirements.txt
```

### スキルが古いバージョン

**解決方法**:
```bash
# スキルを再インストール
cd ~/.claude/skills
rm -rf skill-creator
npx degit anthropics/skills/skill-creator skill-creator
```

---

## 📚 参考リソース

### 公式リソース
- **Anthropic Skills GitHub**: https://github.com/anthropics/skills
- **Claude Skills 公式発表**: https://www.anthropic.com/news/skills
- **Skills ドキュメント**: https://docs.claude.com/en/docs/claude-code/skills

### コミュニティリソース
- **Awesome Claude Skills**: https://github.com/travisvn/awesome-claude-skills
- **Simon Willison's Blog**: https://simonwillison.net/2025/Oct/16/claude-skills/

---

## 💡 ベストプラクティス

### スキル作成時
1. **明確な description を書く**: Claude がスキルを正しく選択できるよう、いつ使うべきかを具体的に記載
2. **手順書形式で記述**: 命令形（"Do X"）で書く、二人称（"You should"）は避ける
3. **参照ファイルを活用**: 詳細情報は `references/` に分離し、SKILL.md はシンプルに保つ
4. **スクリプトを活用**: 繰り返し実行するコードはスクリプト化

### スキル使用時
1. **自動選択を信頼**: 基本的にClaude が適切なスキルを選ぶ
2. **具体的に依頼**: 「PDFを作って」より「見積書をPDF形式で作って」の方が良い
3. **フィードバックで改善**: スキルの動作を見て、必要に応じてSKILL.md を更新

---

## 🎓 次のステップ

1. **スキルを使ってみる**
   - 簡単なタスクから始める（例: 「このテキストをPDFにして」）

2. **カスタムスキルを作成**
   - BSFプロジェクト専用のデータ分析スキルを作成
   - センサーデータ処理の自動化

3. **スキルを共有**
   - チーム内で有用なスキルを共有
   - GitHub にパブリックスキルを公開

---

**以上**

Claude Skills を活用して、BSF-LoopTechプロジェクトの開発効率を向上させましょう！
