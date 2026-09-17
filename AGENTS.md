# POSTING MAP — AGENTS.md (基本就業規則)

## 1. Architecture — ABSOLUTE

- POSTING MAP is a standalone application and a standalone repository.
- Each district is an independent application and repository.
- active/ = district-agnostic universal engine. Never modify active/ for district specialization.
- data/ = district-specific data and client configuration (address_master.csv, boundaries.geojson, municipality_master.csv, config.js, area_mapping.json).
- Spreadsheet = Pure DB. No scripts allowed inside.
- GAS = Standalone only.
- Container-bound Apps Script is NOT part of the current architecture. Never create, restore, synchronize, or depend on it.
- District identity comes dynamically from Spreadsheet name and data/. Never hardcode district names, IDs, or endpoints in active/.

## 2. District Independence — ABSOLUTE

- Each district must operate 100% independently.
- A new district is created by copying Universal POSTING MAP and replacing data/.
- No cross-district repository, branch, code, data, or runtime dependency.
- All production resources (Spreadsheet, GAS, Drive, LIFF) are strictly isolated per district.

## 3. Execution — ABSOLUTE

- No Plan → No Proceed → No Implementation.
- Never expand scope without approval.
- Discover unexpected conditions → Report → STOP.
- Never claim PASS without objective evidence.

## 4. Data Protection

- Never modify production data outside approved scope.
- Never delete production resources without explicit approval.
- Preserve rollback until final verification passes.

## 5. Completion

- Implementation → Test → Diff/Audit → Commit → Push → Deploy → Runtime Verify.
- If any required verification FAILS: STOP.
- Git PASS is not deployment PASS.
- Production deployment requires production runtime evidence.

## 6. Detailed Rules & Workflows

AI社員は作業フェーズに応じて、必ず以下の詳細規程・ワークフローを参照・遵守すること。

- 現行アーキテクチャ定義: [docs/architecture/CURRENT_ARCHITECTURE.md](docs/architecture/CURRENT_ARCHITECTURE.md)
- 開発・完了報告手順: [.agents/workflows/development/workflow.md](.agents/workflows/development/workflow.md)
- 検証・検品規程 & HARD STOP条件: [.agents/rules/verification-gates.md](.agents/rules/verification-gates.md)
- 権限境界・Scope最小化・禁止事項: [.agents/rules/agent-authority.md](.agents/rules/agent-authority.md)
- 新地区展開ワークフロー: [.agents/workflows/district-deployment/workflow.md](.agents/workflows/district-deployment/workflow.md)
- AI社員基盤・アーキテクチャ体系: [docs/ai-foundation.md](docs/ai-foundation.md)

## 7. リポジトリ境界・他地区参照禁止【永久原則】 — ABSOLUTE

POSTING MAPは「1地区 = 1アプリ = 1独立リポジトリ」を基本単位とする。

AIエージェントは、現在作業対象として指定されたリポジトリの境界外にある
他のリポジトリ、地区フォルダー、プロジェクトフォルダー、ファイルを、
通常時・監査時・実装時を問わず、参照・探索・検索・読み取りしてはならない。

### 禁止事項

- 他地区のリポジトリを覗く
- SSD上の別地区フォルダーを探索する
- 他リポジトリのコード・データ・設定を読む
- 他リポジトリのGit履歴・コミット・ブランチを確認する
- 他リポジトリの監査結果やRuntime情報を読む
- 他地区を比較対象として参照する
- 「参考」「比較」「検証」の目的で他リポジトリを開く
- 現在のリポジトリの判断材料を他地区から補完する

### 境界

作業開始時に現在の作業対象リポジトリのGit rootを確定する。

以後、AIエージェントの探索・検索・読み取り範囲は、
そのGit root配下に限定する。

Git root外の情報は、AIエージェントが物理的にアクセス可能であっても
「利用可能な情報」とみなしてはならない。

### 例外

ユーザーが明示的に別リポジトリを対象として指定した場合のみ、
現在の作業を終了・切り替えたうえで、そのリポジトリを新しい作業対象として扱う。

複数リポジトリを同時に参照してはならない。

### 判断不能時

現在のリポジトリ内部だけでは判断できない事項について、
他リポジトリを参照して推測・補完してはならない。

必要な場合は `UNDETERMINED` と明示し、ユーザーに確認する。

### 最上位原則

「アクセスできる」と「参照してよい」は同義ではない。

現在の作業対象以外のリポジトリは、
存在していても、AIエージェントにとっては存在しないものとして扱う。
