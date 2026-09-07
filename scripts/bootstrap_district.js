#!/usr/bin/env node

/**
 * POSTING MAP - Automated District Bootstrap Script
 * 
 * 責務:
 * デプロイされたスタンドアロンGAS Web Appに対して非対話型で
 * DISTRICT_ID, TARGET_SPREADSHEET_ID, STORAGE_PARENT_ID を Script Properties へ自動注入する。
 * 人間によるGASエディタ操作を完全に排除する。
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const rootDir = path.resolve(__dirname, '..');

async function main() {
  console.log('====================================================');
  console.log('🚀 POSTING MAP - Automated District Bootstrapper');
  console.log('====================================================\n');

  // 1. Read deployment.json for Web App URL and IDs
  const deploymentPath = path.join(rootDir, 'deployment.json');
  if (!fs.existsSync(deploymentPath)) {
    console.error(`❌ Error: deployment.json not found at: ${deploymentPath}`);
    process.exit(1);
  }

  const deployment = JSON.parse(fs.readFileSync(deploymentPath, 'utf8'));
  const webAppUrl = process.env.WEB_APP_URL || deployment?.resources?.webAppUrl || deployment?.webAppUrl;
  const districtId = process.env.DISTRICT_ID || deployment?.districtId;
  const targetSpreadsheetId = process.env.TARGET_SPREADSHEET_ID || deployment?.resources?.spreadsheetId || deployment?.spreadsheetId;
  const storageParentId = process.env.STORAGE_PARENT_ID || deployment?.resources?.storageFolderId || deployment?.storageFolderId;

  if (!webAppUrl) {
    console.error('❌ Error: Web App URL is required (in deployment.json or env WEB_APP_URL)');
    process.exit(1);
  }
  if (!districtId) {
    console.error('❌ Error: District ID is required (in deployment.json or env DISTRICT_ID)');
    process.exit(1);
  }
  if (!targetSpreadsheetId) {
    console.error('❌ Error: Target Spreadsheet ID is required (in deployment.json or env TARGET_SPREADSHEET_ID)');
    process.exit(1);
  }
  if (!storageParentId) {
    console.error('❌ Error: Storage Parent ID is required (in deployment.json or env STORAGE_PARENT_ID)');
    process.exit(1);
  }

  // 2. Resolve Provisioning Token
  let provisioningToken = (process.env.POSTING_MAP_PROVISIONING_TOKEN || '').trim();
  if (!provisioningToken) {
    const envPath = path.join(rootDir, '.env');
    if (fs.existsSync(envPath)) {
      const envText = fs.readFileSync(envPath, 'utf8');
      for (const line of envText.split(/\r?\n/)) {
        const match = line.match(/^\s*POSTING_MAP_PROVISIONING_TOKEN\s*=\s*(.*)$/);
        if (match) {
          provisioningToken = match[1].trim().replace(/^['"]|['"]$/g, '');
          break;
        }
      }
    }
  }

  if (!provisioningToken || provisioningToken.length < 16) {
    console.error('❌ Error: POSTING_MAP_PROVISIONING_TOKEN (at least 16 characters) is required.');
    console.error('   Please run: export POSTING_MAP_PROVISIONING_TOKEN="<your-secret-token>"');
    process.exit(1);
  }

  console.log(`📌 Target District:        ${districtId}`);
  console.log(`📌 Target Spreadsheet ID:  ${targetSpreadsheetId}`);
  console.log(`📌 Storage Parent ID:      ${storageParentId}`);
  console.log(`📌 Web App Endpoint:       ${webAppUrl}`);
  console.log(`🔒 Provisioning Token:     ${provisioningToken.substring(0, 4)}...${provisioningToken.substring(provisioningToken.length - 4)} (${provisioningToken.length} chars)\n`);

  // 3. Send bootstrapEnvironment POST request
  console.log('📡 Sending bootstrapEnvironment request to Web App...');
  const payload = {
    action: 'bootstrapEnvironment',
    provisioningToken: provisioningToken,
    districtId: districtId,
    targetSpreadsheetId: targetSpreadsheetId,
    storageParentId: storageParentId,
    options: {
      provisioningToken: provisioningToken
    }
  };

  try {
    const response = await fetch(webAppUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(payload),
      redirect: 'follow'
    });

    const responseText = await response.text();
    let result;
    try {
      result = JSON.parse(responseText);
    } catch (e) {
      console.error(`❌ Failed to parse JSON response (${response.status}):\n${responseText}`);
      process.exit(1);
    }

    if (!result.success) {
      console.error(`❌ Bootstrap Failed: [${result.code || 'ERROR'}] ${result.message}`);
      process.exit(1);
    }

    console.log('✅ Bootstrap SUCCESS:', result.message);
    console.log(`   District:              ${result.districtId}`);
    console.log(`   Target Spreadsheet ID: ${result.targetSpreadsheetId}`);
    console.log(`   Storage Parent ID:     ${result.storageParentId}\n`);

    // 4. Health Check verification
    console.log('🔍 Running automated Health Check (getSystemSummary)...');
    const healthUrl = `${webAppUrl}?action=getSystemSummary`;
    const healthRes = await fetch(healthUrl, { redirect: 'follow' });
    const healthText = await healthRes.text();
    const healthJson = JSON.parse(healthText);

    if (healthJson.success && healthJson.districtName === districtId) {
      console.log('🟢 HEALTH CHECK PASSED:');
      console.log(`   District Name SSOT:    ${healthJson.districtName} (Matched!)`);
      console.log(`   Online Status:         ${healthJson.online}`);
      console.log(`   Total / Done:          ${healthJson.total || 0} / ${healthJson.done || 0}`);
    } else {
      console.error('⚠️  Health check returned unexpected response:', healthJson);
      process.exit(1);
    }

    console.log('\n🎉 ALL BOOTSTRAP & HEALTH CHECKS COMPLETED SUCCESSFULLY!');
  } catch (err) {
    console.error('❌ Request error:', err.message);
    process.exit(1);
  }
}

main();
