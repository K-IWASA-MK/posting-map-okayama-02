# POSTING MAP — AGENTS.md (基本就業規則)

## 1. Architecture — ABSOLUTE

- Spreadsheet = Pure DB / GAS = Standalone only.
- Container-bound Apps Script is NOT part of the current architecture.
- Current architecture is authoritative; legacy implementations that are not part of the current architecture must not be restored, synchronized, or treated as active architecture.
- Never create, restore, synchronize, or depend on container-bound GAS.
- Existing container-bound GAS found in a copied Spreadsheet is legacy residue.

## 2. District Independence — ABSOLUTE

- Each district is an independent repository/application.
- No cross-district merge, shared branch, or code/data contamination.
- District identity comes only from Spreadsheet name and data/.
- Never hardcode district names, IDs, or locations in active/.

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

- 開発・完了報告手順: [.agents/workflows/development/workflow.md](.agents/workflows/development/workflow.md)
- 検証・検品規程 & HARD STOP条件: [.agents/rules/verification-gates.md](.agents/rules/verification-gates.md)
- 権限境界・Scope最小化・禁止事項: [.agents/rules/agent-authority.md](.agents/rules/agent-authority.md)
- 新地区展開ワークフロー: [.agents/workflows/district-deployment/workflow.md](.agents/workflows/district-deployment/workflow.md)
- AI社員基盤・アーキテクチャ体系: [docs/ai-foundation.md](docs/ai-foundation.md)
