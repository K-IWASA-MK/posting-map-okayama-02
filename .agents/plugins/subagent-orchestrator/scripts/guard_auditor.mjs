#!/usr/bin/env node

import { existsSync, readFileSync } from 'node:fs';
import { resolve, join } from 'node:path';

function getStdin() {
  return new Promise((resolvePromise) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => data += chunk);
    process.stdin.on('end', () => resolvePromise(data));
  });
}

const DESTRUCTIVE_COMMAND_PATTERNS = [
  /\brm\b/,
  /\bmv\b/,
  /\bgit\s+(commit|push|rebase|merge|reset|checkout\s+-b)\b/,
  /\bsed\s+-i\b/,
  />\s*[^&]/,
  /\btruncate\b/
];

function isDestructiveCommand(commandLine = '') {
  return DESTRUCTIVE_COMMAND_PATTERNS.some(pattern => pattern.test(commandLine));
}

function isAuditorSession(conversationId, workspacePath) {
  if (!conversationId) return false;

  const registryPath = join(workspacePath || process.cwd(), '.agents', 'audit-log', 'active-auditors.json');
  if (existsSync(registryPath)) {
    try {
      const activeAuditors = JSON.parse(readFileSync(registryPath, 'utf8'));
      if (Array.isArray(activeAuditors) && activeAuditors.includes(conversationId)) {
        return true;
      }
    } catch {}
  }

  return false;
}

async function main() {
  const rawInput = await getStdin();
  if (!rawInput.trim()) {
    console.log(JSON.stringify({ decision: 'allow' }));
    return;
  }

  let payload;
  try {
    payload = JSON.parse(rawInput);
  } catch (err) {
    console.log(JSON.stringify({ decision: 'allow' }));
    return;
  }

  const { toolCall, conversationId, workspacePaths } = payload;
  const workspacePath = (workspacePaths && workspacePaths[0]) || process.cwd();

  if (!isAuditorSession(conversationId, workspacePath)) {
    console.log(JSON.stringify({ decision: 'allow' }));
    return;
  }

  const toolName = toolCall?.name || '';
  const args = toolCall?.args || {};

  const FILE_EDIT_TOOLS = [
    'replace_file_content',
    'multi_replace_file_content',
    'write_to_file'
  ];

  if (FILE_EDIT_TOOLS.includes(toolName)) {
    console.log(JSON.stringify({
      decision: 'deny',
      reason: `[Auditor Guard Violation] The Auditor is strictly READ ONLY. Tool "${toolName}" is physically blocked by .agents/plugins/subagent-orchestrator/hooks.json.`
    }));
    return;
  }

  if (toolName === 'run_command') {
    const cmd = args.CommandLine || '';
    if (isDestructiveCommand(cmd)) {
      console.log(JSON.stringify({
        decision: 'deny',
        reason: `[Auditor Guard Violation] Destructive command detected ("${cmd}"). The Auditor is strictly prohibited from modifying files or state.`
      }));
      return;
    }
  }

  console.log(JSON.stringify({ decision: 'allow' }));
}

main().catch(() => {
  console.log(JSON.stringify({ decision: 'allow' }));
});
