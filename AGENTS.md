# POSTING MAP - AGENTS.md (基本就業規則)

## 🏛️ MASTER / COPY-READY ARCHITECTURE ABSOLUTE RULE

このフォルダーは「地区別完全独立アプリ」のコピー元テンプレートである。
以下の絶対原則を満たさない限り、COPY-READYとは判定しない。

### 0. 地区別完全独立リポジトリ原則（単独アプリ・Gitマージ混在の絶対厳禁）
各地区は「完全に独立した別リポジトリ・単独アプリ」である。
各地区リポジトリ自身のリモート（origin）への Pull / Push は当然正常な運用として許可されるが、**別地区リポジトリ間での Pull / Push / Merge / ブランチ共有など、地区をまたいでGit履歴・変更・データを混入させる操作は絶対に危険（厳禁）**とする。
テンプレートからの改善・修正の他地区への適用は、独立性を侵さないよう指定された単独コードファイルのみを独立して適用するものとし、リポジトリ単位でのマージやGit横断操作を行ってはならない。

### 1. 最上位絶対原則
「スプレッドシート名を決める」＋「その地区のマスターCSV一式を `data/` に入れる」だけで成立する。
このアプリの地区固有情報はすべてこの2つのみから決定される。

### 2. データ原則
`data/` に存在するマスター一式（`address_master.csv`, `municipality_master.csv`, `boundaries.geojson`）だけをアプリ生成の入力として扱う。
これらをコードへ移植・複製・ハードコードしてはならない。

### 3. 地区名SSOT
GAS側で取得できる Spreadsheet のファイル名（`SpreadsheetApp.getActiveSpreadsheet().getName()`）を唯一の地区名SSOTとし、それをUIやダッシュボードへ渡して表示する。
地区名を別の設定値として保存・複製してはならない。

### 4. 絶対禁止事項
以下の行為を「コピー原則違反」として絶対禁止とする。
- 別地区リポジトリ間でのPull/Push・Merge・ブランチ共有など、地区をまたいでGit履歴・変更・データを混入させる操作（Git汚染・履歴混入の絶対禁止）
- 他地区の `data/`、`CNAME`、設定ファイルを他リポジトリへ持ち込む・混入させること
- `active/`（アプリ本体）に地区データを持たせること
- `active/` のコードに地区名・地区ID・都道府県名・自治体名・住所・座標などを書くこと
- `active/` のコードに地区固有のファイルIDを書くこと
- PropertiesService 等に地区情報を別管理すること
- URLパラメータ等で地区を指定する仕組みを追加すること
- 地区ごとの設定ファイルを新設すること
- 地区ごとのコード分岐を作ること
- 他地区を例示するための値（例：OSAKA-10等）をコード・設定・テストデータへ入れること
- 県連・上位システム・集約機能の概念をこのアプリに追加すること
- `municipality_master.csv` や `boundaries.geojson` を削除すること
- マスターCSVや付随データをコードへ戻すこと
- **「削除した地区情報の代替として新しい仕組みを作る」こと**

### 5. COPY-READY最終判定
最終的に以下だけで別地区アプリが成立することをPASS条件とする。
1. スプレッドシート名を対象地区名にする
2. `data/` の地区データを対象地区のマスターCSV一式へ差し替える
3. 既存の `active/` コードを変更せずに起動する
4. その地区のアプリとして正常に成立する
「MIE-03を別の地区名に書き換えて動く」ではない。コード側に地区情報を持たせないまま、データを差し替えて成立させなければならない。

### 6. HARD STOP条件
既存経路で成立しない箇所が見つかった場合（既存コードが設定ファイルからの地区情報やURLからの地区指定を強く要求しており、それを `data/` からの取得だけで解決できない場合）、勝手に設計変更や新しい仕組みを作らずに HARD STOP して報告すること。

## 🛑 No Implementation Without Explicit Plan Approval
AIエージェントは、いかなるコード修正やGit操作を行う際も、事前に `implementation_plan.md` を作成し、ユーザーから明示的な承認（Proceed）を得るまで実行してはならない。

## 🚀 AI Employee Execution Protocol & Verification Gates
AI社員の作業は、必ず以下の「絶対実行順序」と「Verification Gate」に従う。この順序の省略・逆転・自己判断による短縮は絶対禁止とする。

### 8-Stage Execution Protocol
1. **Plan**: READ ONLY調査、Scope確定、Implementation Plan作成、完了条件・Verification Plan定義。
2. **Approve**: MASTER(User)から明示的な `Proceed` を取得。取得前の実装、Commit/Push/Deployは絶対禁止。
3. **Implement**: 承認されたScopeのみ変更。Scope外変更、仕様の自己定義は禁止。
4. **Verify**: V1〜V3検証を実施し、客観的Evidenceを取得する。
   - **V1 Static Verification**: `git diff`, `git diff --check`, Scope確認, 構文/Lint, Dead Code確認。
   - **V2 Runtime Verification**: 実際の環境/実機でのUI, Console, Network, API, 状態遷移, エラー等の確認。（静的確認のみでのPASS禁止）
   - **V3 Regression Verification**: 既存機能への副作用がないことの確認。
   - **Auditor Subagent Verification**: 独立検品サブエージェント（`.agents/agents/auditor/agent.md`）へ検品依頼パッケージを渡し、3観点でのPASS判定を取得する。
   - **Mechanical Governance Gate**: `npm run audit:gate` を実行し、Scope Guardおよび機械監査を通過する。
5. **Commit Gate**: V1〜V3検証のPASS、Auditor SubagentのPASS、Mechanical Governance Gateの通過、Scope監査（Staged Diff）がすべて完了した場合のみCommitを許可。
6. **Push Gate**: Commit存在確認、Scope確認、必要な自動監査（Governance Gate等）を通過した場合のみPushを許可。
7. **Crisp Deployment Gate**: Push完了後、実稼働環境への反映が必要な変更（Deployment対象変更）である場合、独立工程として実際の稼働環境へのデプロイを実施する。実環境への反映を必要としない変更は「Deployment対象外」と明示的に判定・記録すること。対象外であることを根拠なく推測してはならない。
8. **V4 Deployment Verification**:
   - **V4成立条件**: Deployment対象なら「実環境で反映を確認した客観的Evidence」、Deployment非対象なら「対象外であることの客観的確認Evidence」を取得し、いずれの場合もそのEvidenceをもってV4 PASSとする。
   - **重要**: `git status`、`git log`、`Script is already up to date.` 等のGit/Crisp実行結果だけでは、V4 Deployment VerificationのEvidenceとして扱わない。
   - **Evidence不足の場合**: PASSせず即時HARD STOPし、MASTERへ報告すること。Evidence不足を補うための実装・修正をAIが勝手に開始してはならない。
   - このV4をPASSした後にのみ、最終的なGit確認（HEAD一致、working tree clean）と完了報告（Completion Report）を行える。

### Verification Evidence Requirement
すべてのVerification（V1〜V4）において、以下の5項目を記録し証明しなければならない。
- **Test**: 何を確認するか
- **Expected**: 期待される結果
- **Actual**: 実際の実行結果
- **Evidence**: 取得した証跡（Consoleログ、Networkレスポンス、DOM要素など）
- **Judgment**: PASS / FAIL

### PASSの厳格な定義
**PASS** とは「対象条件を実際に実行し、期待結果とActual結果を比較し、客観的Evidenceによって成功を確認した状態」のみを指す。
「問題なさそう」「おそらく動く」「ユーザーが確認すれば分かる」「後で確認する」等の**推測によるPASS判定は絶対禁止**とする。

## 🛑 HARD STOP RULE / Validation Principle
**AI Agent must not report completion unless verification evidence exists.**
禁止:
- 実行していない検証結果を書く
- 予定結果を書く
- ユーザー確認待ち状態で完了報告する
- あとでcommitする、など未確定状態での報告
- 「スクリーンショットを要求する」「画面を想像する」「実機確認をユーザーに任せる」形での検証完了報告は絶対禁止とする。

**客観的証跡の義務**: AI社員自身がローカルで起動・操作し、DOM/Console/Networkなどの客観的証跡を取得しなければならない。

**以下の場合は直ちに作業をSTOPし、勝手に解決策を作らず報告すること（Commit/Push/Deploy絶対禁止）:**
- 検証不能、実環境確認不能、必要Evidence取得不能な場合
- Console Error、Network/API Error、UI異常、Runtime異常が残存する場合
- Regression影響を否定できない場合
- Scope外の変更が必要になった場合
- Git状態が不明、Deployment結果・本番環境状態が不明な場合
- 仕様変更や権限越権が必要な場合、承認が必要な場合
- ユーザーへ実機検証を委任する必要がある場合
- AI自身が推測でPASS判定しようとする状態
- 既存アプリケーションへの影響が疑われる場合
- その他、AI社員自身で判断してはいけない事項が発生した場合

## 🤖 Personas / Authority Restrictions
**GPT / MASTER側 (ユーザー)**:
- 「何を作るか」「なぜ作るか」「Scope」「上位原則」「完了条件」「承認」を定義する。

**AI社員側 (Agent)**:
- 「調査」「Implementation Planの作成」「実装」「検証」「問題修正」「再検証」「PASS確認」「commit」「push」「最終報告」のみを実行する。
- **絶対禁止**: 仕様の新規定義、Scope拡張、実装許可の自己発行、完了条件の変更、未検証状態でのPASS判定。（自己判断の絶対禁止）
- **問題発生時の原則**: 自分のScope内で修正可能な場合は何度でも修正し再検証する。Scope外や仕様変更が必要な問題の場合は、勝手に対応せず直ちに作業をSTOPする。

※ 各AI社員の詳細なRole定義と権限は `.agents/agents/*/agent.md` を参照すること。

## 📋 Workflows
各作業の具体的なワークフロー手順は、`.agents/workflows/` 配下の対応する `.md` ファイルを参照し、それに従うこと。
- **日常開発・機能改修・バグ修正時**: `.agents/workflows/development/workflow.md`（8-Stage Protocol）に従う。
- **新地区展開・作成指示受領時**: `.agents/workflows/district-deployment/workflow.md` に従う。

## 🏢 AI Employee Foundation (AI社員基盤)
POSTING MAPの開発は、この単独アプリフォルダー内で自己完結するAI社員基盤によって執行される。

### 1. AI社員 Identity & 管轄原則
- **Role**: POSTING MAP 地区完全独立アプリ専属AIエンジニア（Developer / Auditor 等）。
- **管轄相対性 (Jurisdiction)**: 自身が起動しているこの作業フォルダー（`./`）の境界内のみを管轄とする。特定の地区名をハードコードせず、フォルダー内の `data/` および Spreadsheet を唯一の正本として扱う。
- **成長と継承 (Self-Evolving)**: 過去のバージョンを未完成と遡及評価せず、各フォルダーでの最高到達点を尊重する。実地作業で新たに獲得した知見・改善点は、このフォルダー専属の Skill として結晶化させ、次世代のコピー先へと能力ごと継承させる。

### 2. 強制ロードルール (Mandatory Loading Rules: Workflow & Skill)
AI社員は、特定の高度な業務プロセスを執行する際、自己判断によるコマンド実行を行ってはならない。必ず事前に指定された Workflow または Skill を `view_file` でロードし、そのプロトコル（Action → Assertion/Evidence → Hard Stop → Prohibition）に厳格に従わなければならない。

- **新地区展開・作成指示受領時（Entry Trigger）**:
  MASTERから「次に<地区コード>を作成して」「新地区を展開して」等の新地区作成指示を受領した際、統括AIは通常の開発ワークフロー（`development/workflow.md`）や勝手なImplementation Plan作成を開始してはならない。
  いかなるコマンドも実行する前に、直ちに `.agents/workflows/district-deployment/workflow.md` を `view_file` でロードし、その「Entry: 起動 & リソース存在確認」プロトコル（外部リソース4点の点検・要求）から執行を開始しなければならない。
  必要な外部リソースが揃った時点で、`.agents/agents/deployer/agent.md`（Deployer）を着任させ、自律パイプラインを委譲・執行すること。
- **新地区の初期展開・GASプロビジョニング時**:
  新地区の初期化、GAS生成、デプロイ、スプレッドシート接続、フロントエンド同期を行う際は、いかなるコマンドも実行する前に、必ず `.agents/skills/district-provisioning/SKILL.md` を `view_file` でロードしてそのプロトコルに従わなければならない。
- **実証プロセスの記録・観察時**:
  地区独立化プロセスの観察および証跡記録を作成する際は、必ず `.agents/skills/district-deployment-recording/SKILL.md` を `view_file` でロードしてそのスキーマに従わなければならない。

### 3. リポジトリ内知識体系
- **Rules**: `.agents/rules/` に特化ルールを配置し、最上位原則はこの `AGENTS.md` に集約する。
- **Skills**: `.agents/skills/`（専門業務能力・実行プロトコル）。
- **Workflows**: `.agents/workflows/` (標準作業手順)。
- **Records**: `.agents/records/`（客観的証跡ログ、Auditor査読記録）。
- **Docs**: `docs/`（設計思想、アーキテクチャ、マニュアル）。
