#!/usr/bin/env node
import fs from 'fs';
import path from 'path';

const rootDir = process.cwd();
const targetRel = process.argv[2] || path.join('data', 'address_master.csv');
const targetFile = path.isAbsolute(targetRel) ? targetRel : path.join(rootDir, targetRel);

console.log('===============================================================');
console.log('🔍 [MASTER CSV QUALITY GATE AUDIT]');
console.log(`Target: ${targetFile}`);
console.log('===============================================================\n');

const allowedCities = new Set([
  '岡山市中区',
  '岡山市東区',
  '岡山市南区',
  '玉野市',
  '瀬戸内市'
]);

const report = {
  ruleResults: {},
  totalLines: 0,
  dataRowCount: 0,
  cityCounts: {},
  rowIdMin: null,
  rowIdMax: null,
  rowIdDuplicates: [],
  rowIdMissing: [],
  townDuplicates: [],
  missingValues: [],
  coordErrors: [],
  scopeErrors: [],
  columnErrors: []
};

// Rule-01: ファイル存在・非ゼロ
if (!fs.existsSync(targetFile)) {
  report.ruleResults['Rule-01'] = { pass: false, message: 'File does not exist' };
  console.error('❌ Rule-01 FAIL: File does not exist');
  process.exit(1);
}

const stats = fs.statSync(targetFile);
if (stats.size === 0) {
  report.ruleResults['Rule-01'] = { pass: false, message: 'File size is 0 bytes' };
  console.error('❌ Rule-01 FAIL: File size is 0 bytes');
  process.exit(1);
}
report.ruleResults['Rule-01'] = { pass: true, sizeBytes: stats.size };
console.log(`✅ Rule-01 PASS: File exists (${stats.size} bytes)`);

// Read file
const rawContent = fs.readFileSync(targetFile, 'utf8');
const lines = rawContent.split(/\r?\n/).filter(line => line.trim().length > 0);
report.totalLines = lines.length;

if (lines.length < 1) {
  report.ruleResults['Rule-02'] = { pass: false, message: 'File has no lines' };
  console.error('❌ Rule-02 FAIL: File has no lines');
  process.exit(1);
}

// Rule-02: ヘッダー完全一致
const expectedHeader = 'rowId,city_name,town_name,latitude,longitude';
const actualHeader = lines[0].trim();
if (actualHeader === expectedHeader) {
  report.ruleResults['Rule-02'] = { pass: true, header: actualHeader };
  console.log(`✅ Rule-02 PASS: Header exactly matches "${expectedHeader}"`);
} else {
  report.ruleResults['Rule-02'] = { pass: false, expected: expectedHeader, actual: actualHeader };
  console.error(`❌ Rule-02 FAIL: Header mismatch. Expected "${expectedHeader}", got "${actualHeader}"`);
}

// Rule-04: データ行1件以上
const dataLines = lines.slice(1);
report.dataRowCount = dataLines.length;
if (dataLines.length >= 1) {
  report.ruleResults['Rule-04'] = { pass: true, count: dataLines.length };
  console.log(`✅ Rule-04 PASS: Data row count is ${dataLines.length} (>= 1)`);
} else {
  report.ruleResults['Rule-04'] = { pass: false, count: 0 };
  console.error('❌ Rule-04 FAIL: No data rows found');
}

// Inspect all data rows
let rule03Pass = true;
let rule06Pass = true;
let rule07Pass = true;
let rule08Pass = true;
let rule09Pass = true;
let rule10Pass = true;
let rule11Pass = true;

const seenRowIds = new Map();
const seenTownKeys = new Map();

dataLines.forEach((lineText, idx) => {
  const lineNum = idx + 2; // 1-indexed (header is line 1)
  const cols = lineText.split(',');

  // Rule-03 & Rule-11: 5列完全一致・列ずれなし
  if (cols.length !== 5) {
    rule03Pass = false;
    rule11Pass = false;
    report.columnErrors.push({ line: lineNum, colCount: cols.length, text: lineText });
  }

  const [rawRowId, rawCity, rawTown, rawLat, rawLng] = cols;

  // Rule-05 check components
  const parsedId = Number(rawRowId);
  if (!Number.isInteger(parsedId) || parsedId < 1 || String(parsedId) !== rawRowId.trim()) {
    report.rowIdMissing.push({ line: lineNum, raw: rawRowId });
  } else {
    if (seenRowIds.has(parsedId)) {
      report.rowIdDuplicates.push({ id: parsedId, line1: seenRowIds.get(parsedId), line2: lineNum });
    } else {
      seenRowIds.set(parsedId, lineNum);
    }
  }

  // Rule-06: city_name非空・カンマなし
  const trimmedCity = (rawCity || '').trim();
  if (!trimmedCity) {
    rule06Pass = false;
    report.missingValues.push({ line: lineNum, field: 'city_name' });
  } else {
    report.cityCounts[trimmedCity] = (report.cityCounts[trimmedCity] || 0) + 1;
    if (!allowedCities.has(trimmedCity)) {
      report.scopeErrors.push({ line: lineNum, city: trimmedCity, town: rawTown });
    }
  }

  // Rule-07: town_name非空・カンマなし
  const trimmedTown = (rawTown || '').trim();
  if (!trimmedTown) {
    rule07Pass = false;
    report.missingValues.push({ line: lineNum, field: 'town_name' });
  } else {
    const townKey = `${trimmedCity}:${trimmedTown}`;
    if (seenTownKeys.has(townKey)) {
      report.townDuplicates.push({ key: townKey, line1: seenTownKeys.get(townKey), line2: lineNum });
    } else {
      seenTownKeys.set(townKey, lineNum);
    }
  }

  // Rule-08 & 09 & 10: 座標検査
  const latNum = parseFloat(rawLat);
  const lngNum = parseFloat(rawLng);

  if (isNaN(latNum) || !isFinite(latNum)) {
    rule08Pass = false;
    report.coordErrors.push({ line: lineNum, field: 'latitude', value: rawLat });
  }
  if (isNaN(lngNum) || !isFinite(lngNum)) {
    rule09Pass = false;
    report.coordErrors.push({ line: lineNum, field: 'longitude', value: rawLng });
  }

  if (isFinite(latNum) && isFinite(lngNum)) {
    // 国内座標範囲: 20 <= lat <= 46, 122 <= lng <= 154
    if (latNum < 20.0 || latNum > 46.0 || lngNum < 122.0 || lngNum > 154.0) {
      rule10Pass = false;
      report.coordErrors.push({ line: lineNum, field: 'boundary', lat: latNum, lng: lngNum });
    }
  }
});

report.ruleResults['Rule-03'] = { pass: rule03Pass, errorCount: report.columnErrors.length };
report.ruleResults['Rule-11'] = { pass: rule11Pass, errorCount: report.columnErrors.length };
report.ruleResults['Rule-06'] = { pass: rule06Pass, errorCount: report.missingValues.filter(m => m.field === 'city_name').length };
report.ruleResults['Rule-07'] = { pass: rule07Pass, errorCount: report.missingValues.filter(m => m.field === 'town_name').length };
report.ruleResults['Rule-08'] = { pass: rule08Pass, errorCount: report.coordErrors.filter(c => c.field === 'latitude').length };
report.ruleResults['Rule-09'] = { pass: rule09Pass, errorCount: report.coordErrors.filter(c => c.field === 'longitude').length };
report.ruleResults['Rule-10'] = { pass: rule10Pass, errorCount: report.coordErrors.filter(c => c.field === 'boundary').length };

// Rule-05: rowId連続性検証
const sortedIds = Array.from(seenRowIds.keys()).sort((a, b) => a - b);
let rule05Pass = true;
if (sortedIds.length !== dataLines.length) {
  rule05Pass = false;
}
if (sortedIds.length > 0) {
  report.rowIdMin = sortedIds[0];
  report.rowIdMax = sortedIds[sortedIds.length - 1];
  if (report.rowIdMin !== 1 || report.rowIdMax !== dataLines.length) {
    rule05Pass = false;
  }
  for (let i = 0; i < sortedIds.length; i++) {
    if (sortedIds[i] !== i + 1) {
      rule05Pass = false;
      break;
    }
  }
} else {
  rule05Pass = false;
}
report.ruleResults['Rule-05'] = {
  pass: rule05Pass,
  min: report.rowIdMin,
  max: report.rowIdMax,
  expectedCount: dataLines.length,
  duplicatesCount: report.rowIdDuplicates.length
};

// Console output
console.log(`${rule03Pass ? '✅' : '❌'} Rule-03 ${rule03Pass ? 'PASS' : 'FAIL'}: 5 columns exact check (${report.columnErrors.length} errors)`);
console.log(`${rule05Pass ? '✅' : '❌'} Rule-05 ${rule05Pass ? 'PASS' : 'FAIL'}: rowId sequence 1..${dataLines.length} (min=${report.rowIdMin}, max=${report.rowIdMax}, duplicates=${report.rowIdDuplicates.length})`);
console.log(`${rule06Pass ? '✅' : '❌'} Rule-06 ${rule06Pass ? 'PASS' : 'FAIL'}: city_name non-empty`);
console.log(`${rule07Pass ? '✅' : '❌'} Rule-07 ${rule07Pass ? 'PASS' : 'FAIL'}: town_name non-empty`);
console.log(`${rule08Pass ? '✅' : '❌'} Rule-08 ${rule08Pass ? 'PASS' : 'FAIL'}: latitude is finite number`);
console.log(`${rule09Pass ? '✅' : '❌'} Rule-09 ${rule09Pass ? 'PASS' : 'FAIL'}: longitude is finite number`);
console.log(`${rule10Pass ? '✅' : '❌'} Rule-10 ${rule10Pass ? 'PASS' : 'FAIL'}: Coordinates within domestic boundary`);
console.log(`${rule11Pass ? '✅' : '❌'} Rule-11 ${rule11Pass ? 'PASS' : 'FAIL'}: No column misalignment`);

// Scope check
const scopePass = report.scopeErrors.length === 0;
console.log(`\n${scopePass ? '✅' : '❌'} Scope Guard: ${scopePass ? 'PASS' : 'FAIL'} (${report.scopeErrors.length} out-of-scope records)`);

console.log('\n📊 [MUNICIPALITY BREAKDOWN]:');
Object.entries(report.cityCounts).forEach(([city, count]) => {
  console.log(`   - ${city}: ${count} records`);
});
console.log(`   TOTAL: ${report.dataRowCount} records`);

console.log('\n📋 [AUDIT SUMMARY JSON]:');
console.log(JSON.stringify({
  allRulesPass: Object.values(report.ruleResults).every(r => r.pass) && scopePass,
  ruleResults: report.ruleResults,
  totalRecords: report.dataRowCount,
  cityCounts: report.cityCounts,
  rowIdRange: `${report.rowIdMin}..${report.rowIdMax}`,
  duplicatesCount: report.townDuplicates.length,
  missingValuesCount: report.missingValues.length,
  coordErrorsCount: report.coordErrors.length,
  scopeErrorsCount: report.scopeErrors.length
}, null, 2));
