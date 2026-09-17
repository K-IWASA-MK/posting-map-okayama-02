import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { execSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { validateResult } from './orchestrator/lib/handover_schema.mjs';

const rootDir = process.cwd();
const verdictPath = resolve(rootDir, '.agents/audit-log/auditor-verdict.json');

const REQUIRED_VIEWPOINTS = [
  'viewpoint1_districtAgnostic',
  'viewpoint2_scopeAndDiff',
  'viewpoint3_objectiveEvidence',
  'viewpoint4_copyResilienceZeroManual',
  'viewpoint5_officialDataGate'
];

function exitFail(reason, details = null) {
  console.error('\n🛑 [Hard Stop] AI Auditor Gate Verification FAILED:');
  console.error(`Reason: ${reason}`);
  if (details) {
    if (Array.isArray(details)) {
      details.forEach(d => console.error(`  - ${typeof d === 'string' ? d : JSON.stringify(d)}`));
    } else if (typeof details === 'object') {
      console.error(`Details: ${JSON.stringify(details, null, 2)}`);
    } else {
      console.error(`Details: ${details}`);
    }
  }
  process.exit(1);
}

// ─────────────────────────────────────────────────────────────
// 【モード: Inspect / Handover 生成モード (--inspect / --handover)】
// ─────────────────────────────────────────────────────────────
if (process.argv.includes('--inspect') || process.argv.includes('--handover')) {
  let stagedDiff = '';
  let stagedFiles = [];
  try {
    stagedDiff = execSync('git diff --cached', { cwd: rootDir, encoding: 'utf8' });
    const rawNames = execSync('git diff --cached --name-only', { cwd: rootDir, encoding: 'utf8' });
    stagedFiles = rawNames.split('\n').map(s => s.trim()).filter(Boolean);
  } catch (err) {
    console.error(`Failed to inspect git status: ${err.message}`);
    process.exit(1);
  }

  const stagedDiffHash = createHash('sha256').update(stagedDiff).digest('hex');

  const handoverSummary = {
    taskId: `audit-${Date.now()}`,
    timestamp: new Date().toISOString(),
    targetAgent: 'auditor',
    action: 'intellectual-review',
    spec: '.agents/agents/auditor/agent.md',
    stagedFiles,
    stagedDiffLength: stagedDiff.length,
    stagedDiffHash,
    readyForReview: stagedFiles.length > 0
  };

  console.log(JSON.stringify(handoverSummary, null, 2));
  process.exit(0);
}

// ─────────────────────────────────────────────────────────────
// 【モード: AI Auditor Gate 検証モード (デフォルト)】
// ─────────────────────────────────────────────────────────────

// 1. Check verdict file existence
if (!existsSync(verdictPath)) {
  exitFail(
    'AI Auditor review has not been executed.',
    'Target file ".agents/audit-log/auditor-verdict.json" is missing. A review by Main AI following .agents/agents/auditor/agent.md is mandatory prior to commit.'
  );
}

// 2. Parse verdict JSON
let verdict;
try {
  const content = readFileSync(verdictPath, 'utf8');
  verdict = JSON.parse(content);
} catch (err) {
  exitFail('AI Auditor verdict file is corrupt or invalid JSON.', err.message);
}

// 3. Schema validation via handover_schema
const { valid, errors } = validateResult(verdict);
if (!valid) {
  exitFail('AI Auditor verdict violates Handover Result Schema.', errors);
}

// 4. Verify Agent identity & spec
if (verdict.agent !== 'auditor') {
  exitFail(`Invalid agent in verdict: expected "auditor", got "${verdict.agent}"`);
}
const spec = verdict.details?.spec;
if (spec !== '.agents/agents/auditor/agent.md') {
  exitFail(`Invalid or missing auditor specification: expected ".agents/agents/auditor/agent.md", got "${spec}"`);
}

// 5. Verify 5 Viewpoints
const viewpoints = verdict.details?.viewpoints;
if (!viewpoints || typeof viewpoints !== 'object') {
  exitFail('Auditor verdict is missing "details.viewpoints" object covering the 5 viewpoints.');
}

const failedViewpoints = [];
for (const vp of REQUIRED_VIEWPOINTS) {
  const item = viewpoints[vp];
  if (!item || typeof item !== 'object') {
    failedViewpoints.push(`${vp}: missing or invalid structure`);
  } else if (item.status !== 'PASS') {
    failedViewpoints.push(`${vp}: status is "${item.status}" (rationale: ${item.rationale || 'none'})`);
  }
}

if (failedViewpoints.length > 0) {
  exitFail('One or more Auditor Viewpoints did not PASS:', failedViewpoints);
}

// 6. Verify overall verdict status
if (verdict.status !== 'PASS') {
  exitFail(`AI Auditor overall status is not PASS (got: "${verdict.status}").`, verdict.issues || []);
}

// 7. Verify READ ONLY Integrity (changedFiles must be strictly empty)
if (!Array.isArray(verdict.changedFiles) || verdict.changedFiles.length > 0) {
  exitFail('Auditor violated READ ONLY constraint: changedFiles must be strictly empty [].');
}

// 8. Staged Diff Hash Binding (Freshness & Anti-Tampering verification)
let stagedDiff = '';
try {
  stagedDiff = execSync('git diff --cached', { cwd: rootDir, encoding: 'utf8' });
} catch (err) {
  exitFail('Failed to execute "git diff --cached" to calculate staged diff hash.', err.message);
}

const currentDiffHash = createHash('sha256').update(stagedDiff).digest('hex');
const auditedDiffHash = verdict.details?.stagedDiffHash;

if (!auditedDiffHash) {
  exitFail('Auditor verdict is missing "details.stagedDiffHash". Cannot verify diff freshness.');
}

if (currentDiffHash !== auditedDiffHash) {
  exitFail(
    'STALE AUDIT DETECTED / Staged Diff Hash Mismatch!',
    [
      `Audited Staged Diff Hash: ${auditedDiffHash}`,
      `Current Staged Diff Hash: ${currentDiffHash}`,
      'The files staged for commit have changed since the AI Auditor performed the intellectual review.',
      'Re-audit by Main AI following .agents/agents/auditor/agent.md is mandatory before commit.'
    ]
  );
}

// All checks passed!
console.log('🟢 [AI Auditor Gate] PASSED: Main AI Intellectual Review verified.');
console.log(`  Auditor: ${verdict.details?.auditor || 'Main AI'}`);
console.log(`  Specification: ${spec}`);
console.log(`  Staged Diff Hash: ${currentDiffHash.substring(0, 16)}...`);
console.log('  Viewpoints (5/5 PASS):');
REQUIRED_VIEWPOINTS.forEach(vp => {
  console.log(`    ✓ ${vp}: PASS`);
});
console.log('  Zero mutations confirmed (READ ONLY integrity maintained).');
process.exit(0);
