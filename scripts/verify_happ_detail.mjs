import { chromium } from 'playwright';
import http from 'http';
import fs from 'fs';
import path from 'path';

const PORT = 8095;
const rootDir = process.cwd();

function startServer() {
  const server = http.createServer((req, res) => {
    let relativePath = req.url.split('?')[0];
    if (relativePath.startsWith('/app/')) {
      relativePath = relativePath.replace('/app/', '/active/dashboard/');
    } else if (relativePath === '/app' || relativePath === '/index.html' || relativePath === '/') {
      relativePath = '/index.html';
    } else if (relativePath.startsWith('/business/')) {
      relativePath = relativePath.replace('/business/', '/active/business/');
    } else if (relativePath.startsWith('/data/')) {
      relativePath = relativePath;
    }
    let filePath = path.join(rootDir, relativePath);
    if (fs.existsSync(filePath) && fs.statSync(filePath).isDirectory()) {
      filePath = path.join(filePath, 'index.html');
    }

    fs.readFile(filePath, (err, data) => {
      if (err) {
        res.writeHead(404);
        res.end(`Not found: ${req.url}`);
      } else {
        let ct = 'text/html; charset=utf-8';
        if (filePath.endsWith('.js')) ct = 'application/javascript; charset=utf-8';
        if (filePath.endsWith('.css')) ct = 'text/css; charset=utf-8';
        if (filePath.endsWith('.json')) ct = 'application/json; charset=utf-8';
        if (filePath.endsWith('.png')) ct = 'image/png';
        if (filePath.endsWith('.csv')) ct = 'text/plain; charset=utf-8';
        res.writeHead(200, { 'Content-Type': ct, 'Access-Control-Allow-Origin': '*' });
        res.end(data);
      }
    });
  });
  return new Promise(r => server.listen(PORT, () => r(server)));
}

async function verifyHApp() {
  const server = await startServer();
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 390, height: 844 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Line/13.0.0'
  });
  const page = await context.newPage();

  await page.route('**/sdk.js', route => {
    route.fulfill({
      status: 200,
      contentType: 'application/javascript',
      body: `
        window.liff = {
          init: () => Promise.resolve(),
          isLoggedIn: () => true,
          getAccessToken: () => 'test-token',
          getIDToken: () => 'test-id',
          getOS: () => 'ios',
          getProfile: () => Promise.resolve({ userId: 'U_TEST', displayName: '配布員A' })
        };
      `
    });
  });

  await page.addInitScript(() => {
    localStorage.setItem('user_info', JSON.stringify({
      id: 'STAFF_OKAYAMA',
      last: '岡山',
      first: '配布員',
      picture: ''
    }));
  });

  console.log('Navigating to H-App on local test server...');
  await page.goto(`http://localhost:${PORT}/app/index.html`, { waitUntil: 'networkidle', timeout: 20000 });
  await page.waitForTimeout(3000);

  const checkData = await page.evaluate(async () => {
    let pinsCount = 0;
    let citiesList = [];
    if (window.AddressMasterService) {
      try {
        const pins = await window.AddressMasterService.getInstance().getAll();
        pinsCount = pins.length;
        const cities = await window.AddressMasterService.getInstance().getCities();
        citiesList = cities.map(c => ({ name: c.name, count: c.count }));
      } catch (e) {
        console.error('AddressMasterService error:', e);
      }
    }
    
    const cfg = window.PMS_CLIENT_CONFIG || {};

    return {
      pinsCount,
      citiesList,
      liffId: cfg.line?.liffId,
      gasUrl: cfg.api?.gasWebAppUrl
    };
  });

  console.log('\n=== H-APP RUNTIME VERIFICATION RESULTS ===');
  console.log('Configuration LIFF ID:', checkData.liffId);
  console.log('Configuration GAS URL:', checkData.gasUrl);
  console.log('Loaded Master Pins Count:', checkData.pinsCount);
  console.log('Recognized Cities List:', checkData.citiesList);

  const screenshotPath = '/Users/katsujiiwasa/.gemini/antigravity-ide/brain/9897e06b-c2f9-41e9-9263-d165ccbd06ec/h_app_okayama02_verification.png';
  await page.screenshot({ path: screenshotPath, fullPage: true });
  console.log(`Saved verification screenshot to: ${screenshotPath}`);

  await browser.close();
  server.close();

  if (checkData.liffId !== '2010941735-8FCwjD6x') {
    throw new Error(`LIFF ID mismatch: expected 2010941735-8FCwjD6x, got ${checkData.liffId}`);
  }
  if (checkData.pinsCount !== 508) {
    throw new Error(`Pins count mismatch: expected 508, got ${checkData.pinsCount}`);
  }
  console.log('\n✅ All H-App Runtime Assertions Passed!');
}

verifyHApp().catch(err => {
  console.error('❌ Verification failed:', err);
  process.exit(1);
});
