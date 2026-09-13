#!/usr/bin/env node

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { execFileSync } from 'node:child_process';

const CANDIDATE_AGENTAPI_PATHS = [
  resolve(process.env.HOME || '', '.gemini/antigravity-ide/bin/agentapi'),
  resolve(process.env.HOME || '', '.gemini/antigravity/bin/agentapi'),
  '/Applications/Antigravity IDE.app/Contents/Resources/app/extensions/antigravity/bin/language_server_macos_arm'
];

function resolveAgentApi() {
  for (const p of CANDIDATE_AGENTAPI_PATHS) {
    if (existsSync(p)) {
      return p;
    }
  }
  return 'agentapi';
}

function findWorkspaceRoot(startDir = process.cwd()) {
  let curr = resolve(startDir);
  while (curr !== resolve(curr, '..')) {
    if (existsSync(join(curr, '.agents')) || existsSync(join(curr, '.git'))) {
      return curr;
    }
    curr = resolve(curr, '..');
  }
  return process.cwd();
}

function getAvailableAgents(workspaceRoot) {
  const agentsDir = join(workspaceRoot, '.agents', 'agents');
  if (!existsSync(agentsDir)) return [];
  try {
    return readdirSync(agentsDir, { withFileTypes: true })
      .filter(d => d.isDirectory() && existsSync(join(agentsDir, d.name, 'agent.md')))
      .map(d => d.name);
  } catch {
    return [];
  }
}

const TOOLS = [
  {
    name: 'invoke_subagent',
    description: 'Invoke a dedicated POSTING MAP AI employee (subagent) with a specific role defined in .agents/agents/<name>/agent.md. Automatically loads role instructions, injects parent conversation ID, spawns an isolated child conversation via agentapi, and sets up return communication protocol.',
    inputSchema: {
      type: 'object',
      properties: {
        agent_name: {
          type: 'string',
          description: 'Name of the target AI employee (e.g. "auditor", "deployer", "district-deployment-recorder"). Must match a folder under .agents/agents/.'
        },
        task: {
          type: 'string',
          description: 'Detailed task description and instructions for the subagent to perform.'
        },
        model: {
          type: 'string',
          enum: ['flash', 'pro', 'flash_lite'],
          description: 'Model tier for the subagent. Defaults to "flash".'
        },
        title: {
          type: 'string',
          description: 'Optional title for the subagent conversation window.'
        },
        parent_conversation_id: {
          type: 'string',
          description: 'Parent conversation ID to receive completion report. If omitted, will attempt detection or require prompt insertion.'
        }
      },
      required: ['agent_name', 'task']
    }
  },
  {
    name: 'send_subagent_message',
    description: 'Send a message to another agent conversation (e.g. parent reporting, inter-agent coordination) via agentapi send-message.',
    inputSchema: {
      type: 'object',
      properties: {
        recipient_id: {
          type: 'string',
          description: 'Target conversation ID to receive the message.'
        },
        content: {
          type: 'string',
          description: 'Message content to send.'
        },
        title: {
          type: 'string',
          description: 'Optional message title.'
        }
      },
      required: ['recipient_id', 'content']
    }
  }
];

async function handleInvokeSubagent(args) {
  const { agent_name, task, model = 'flash', title, parent_conversation_id } = args;
  const workspaceRoot = findWorkspaceRoot();
  const agentMdPath = join(workspaceRoot, '.agents', 'agents', agent_name, 'agent.md');

  if (!existsSync(agentMdPath)) {
    const available = getAvailableAgents(workspaceRoot);
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: `[Error] Agent "${agent_name}" not found at ${agentMdPath}.\nAvailable agents in this workspace: ${available.join(', ') || 'None'}`
        }
      ]
    };
  }

  const agentMdContent = readFileSync(agentMdPath, 'utf8');
  const agentApiBin = resolveAgentApi();

  const reportingSection = parent_conversation_id
    ? `## 完了報告プロトコル（必須執行）\n作業が完了したら、必ず以下のコマンドを実行して親会話へ完了結果を報告せよ：\n${agentApiBin} send-message --title="[完了報告] ${agent_name}" "${parent_conversation_id}" "<最終報告と客観的証跡(Evidence)>"`
    : `## 完了報告プロトコル（必須執行）\n作業が完了したら、親会話または担当者へ客観的証跡（Evidence）と合否判定（PASS/FAIL）を明確に報告せよ。`;

  const combinedPrompt = [
    `# 【AI社員着任辞令】${agent_name.toUpperCase()}`,
    `あなたはPOSTING MAP OS専任AI社員「${agent_name}」として任命された。以下の agent.md に規定されたRole、責務、権限境界、絶対禁止事項を唯一の行動原則として厳格に遵守せよ。`,
    '',
    '--- START OF AGENT DEFINITION ---',
    agentMdContent,
    '--- END OF AGENT DEFINITION ---',
    '',
    '## 委譲された業務タスク (Assigned Task)',
    task,
    '',
    reportingSection
  ].join('\n');

  const cmdArgs = [];
  if (agentApiBin.endsWith('language_server_macos_arm')) {
    cmdArgs.push('agentapi');
  }
  cmdArgs.push('new-conversation');
  if (model) {
    cmdArgs.push(`--model=${model}`);
  }
  if (title || agent_name) {
    cmdArgs.push(`--title=${title || `AI-Employee: ${agent_name}`}`);
  }
  cmdArgs.push(combinedPrompt);

  try {
    const output = execFileSync(agentApiBin, cmdArgs, {
      cwd: workspaceRoot,
      encoding: 'utf8',
      timeout: 30000
    });

    if (agent_name.toLowerCase().includes('auditor')) {
      try {
        const auditLogDir = join(workspaceRoot, '.agents', 'audit-log');
        const activeAuditorsPath = join(auditLogDir, 'active-auditors.json');
        let convoId = null;
        try {
          const parsed = JSON.parse(output);
          convoId = parsed?.response?.conversationId || parsed?.response?.conversationMetadata?.metadata?.rootConversationId;
        } catch {}

        if (convoId) {
          let list = [];
          if (existsSync(activeAuditorsPath)) {
            try { list = JSON.parse(readFileSync(activeAuditorsPath, 'utf8')); } catch {}
          }
          if (!list.includes(convoId)) {
            list.push(convoId);
            import('node:fs').then(fs => fs.writeFileSync(activeAuditorsPath, JSON.stringify(list, null, 2)));
          }
        }
      } catch (logErr) {
        process.stderr.write(`[Warning] Could not record active auditor: ${logErr.message}\n`);
      }
    }

    return {
      content: [
        {
          type: 'text',
          text: `[Subagent Spawned Successfully]\nAgent: ${agent_name}\nModel: ${model}\nCommand Output:\n${output}\n\nSubagent has been launched in an isolated session. It will follow ${agent_name}/agent.md rules and report back.`
        }
      ]
    };
  } catch (err) {
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: `[Failed to spawn subagent]\nCommand: ${agentApiBin} ${cmdArgs.join(' ')}\nError: ${err.message}\nStderr: ${err.stderr || ''}`
        }
      ]
    };
  }
}

async function handleSendMessage(args) {
  const { recipient_id, content, title } = args;
  const agentApiBin = resolveAgentApi();
  const workspaceRoot = findWorkspaceRoot();

  const cmdArgs = [];
  if (agentApiBin.endsWith('language_server_macos_arm')) {
    cmdArgs.push('agentapi');
  }
  cmdArgs.push('send-message');
  if (title) {
    cmdArgs.push(`--title=${title}`);
  }
  cmdArgs.push(recipient_id);
  cmdArgs.push(content);

  try {
    const output = execFileSync(agentApiBin, cmdArgs, {
      cwd: workspaceRoot,
      encoding: 'utf8',
      timeout: 15000
    });

    return {
      content: [
        {
          type: 'text',
          text: `[Message Sent Successfully]\nRecipient: ${recipient_id}\nOutput: ${output}`
        }
      ]
    };
  } catch (err) {
    return {
      isError: true,
      content: [
        {
          type: 'text',
          text: `[Failed to send message]\nRecipient: ${recipient_id}\nError: ${err.message}\nStderr: ${err.stderr || ''}`
        }
      ]
    };
  }
}

async function processRequest(request) {
  const { id, method, params } = request;

  if (method === 'initialize') {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: {
          tools: {}
        },
        serverInfo: {
          name: 'subagent-orchestrator',
          version: '1.0.0'
        }
      }
    };
  }

  if (method === 'notifications/initialized') {
    return null;
  }

  if (method === 'tools/list') {
    return {
      jsonrpc: '2.0',
      id,
      result: {
        tools: TOOLS
      }
    };
  }

  if (method === 'tools/call') {
    const toolName = params?.name;
    const toolArgs = params?.arguments || {};

    if (toolName === 'invoke_subagent') {
      const toolResult = await handleInvokeSubagent(toolArgs);
      return {
        jsonrpc: '2.0',
        id,
        result: toolResult
      };
    }

    if (toolName === 'send_subagent_message') {
      const toolResult = await handleSendMessage(toolArgs);
      return {
        jsonrpc: '2.0',
        id,
        result: toolResult
      };
    }

    return {
      jsonrpc: '2.0',
      id,
      error: {
        code: -32601,
        message: `Tool not found: ${toolName}`
      }
    };
  }

  if (method === 'ping') {
    return {
      jsonrpc: '2.0',
      id,
      result: {}
    };
  }

  return {
    jsonrpc: '2.0',
    id,
    error: {
      code: -32601,
      message: `Method not found: ${method}`
    }
  };
}

function startServer() {
  let buffer = '';

  process.stdin.on('data', async (chunk) => {
    buffer += chunk.toString();

    while (true) {
      const newlineIdx = buffer.indexOf('\n');
      if (newlineIdx === -1) break;

      let line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);

      if (!line) continue;

      if (line.toLowerCase().startsWith('content-length:')) {
        continue;
      }

      try {
        const request = JSON.parse(line);
        const response = await processRequest(request);
        if (response) {
          process.stdout.write(JSON.stringify(response) + '\n');
        }
      } catch (err) {
        process.stderr.write(`[MCP Error] Failed to parse JSON: ${line} (${err.message})\n`);
      }
    }
  });

  process.stdin.resume();
  process.stderr.write('[subagent-orchestrator] MCP Server ready on stdio.\n');
}

startServer();
