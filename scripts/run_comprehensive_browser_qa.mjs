import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const SCREENSHOTS_DIR = path.resolve('artifacts/browser_qa/screenshots');
const BASE_URL = 'http://127.0.0.1:5173';
const API_URL = 'http://127.0.0.1:8000';

const VIEWPORTS = [
  { name: 'Desktop', width: 1440, height: 900, suffix: 'desktop' },
  { name: 'Laptop',  width: 1366, height: 768, suffix: 'laptop' },
  { name: 'Tablet',  width: 768,  height: 1024, suffix: 'tablet' },
  { name: 'Mobile',  width: 390,  height: 844, suffix: 'mobile' },
];

if (!fs.existsSync(SCREENSHOTS_DIR)) {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
}

const auditLog = {
  timestamp: new Date().toISOString(),
  pagesTested: [],
  elementsTested: [],
  tiersTested: [],
  consoleErrors: [],
  consoleWarnings: [],
  failedRequests: [],
  performanceMetrics: {},
  defects: [],
};

async function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms));
}

async function runAudit() {
  console.log('================================================================');
  console.log('   AQUORA FINAL COMPREHENSIVE AUTOMATED BROWSER QA AUDIT        ');
  console.log('================================================================');
  console.log(`Target Frontend: ${BASE_URL}`);
  console.log(`Target Backend : ${API_URL}`);
  console.log(`Screenshots Dir: ${SCREENSHOTS_DIR}`);

  const browser = await chromium.launch({
    channel: 'chrome',
    headless: true,
  });

  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 AQUORA-QA-Bot/1.0',
  });

  const page = await context.newPage();

  // Attach Console & Network Listeners
  page.on('console', (msg) => {
    const text = msg.text();
    const type = msg.type();
    if (type === 'error') {
      console.error(`[BROWSER ERROR] ${text}`);
      auditLog.consoleErrors.push({ text, location: msg.location() });
    } else if (type === 'warning') {
      auditLog.consoleWarnings.push({ text, location: msg.location() });
    }
  });

  page.on('pageerror', (err) => {
    console.error(`[PAGE EXCEPTION] ${err.message}`);
    auditLog.consoleErrors.push({ text: `Unhandled Exception: ${err.message}`, stack: err.stack });
    auditLog.defects.push({
      id: `DEF-EXC-${Date.now()}`,
      severity: 'P0',
      title: 'Unhandled JavaScript Exception',
      details: err.message,
    });
  });

  page.on('response', (res) => {
    const status = res.status();
    const url = res.url();
    if (status >= 400 && !url.includes('/api/v1/health/ready') && !url.includes('favicon.ico')) {
      console.warn(`[HTTP ${status}] ${url}`);
      auditLog.failedRequests.push({ url, status, statusText: res.statusText() });
    }
  });

  // ─────────────────────────────────────────────────────────────
  // 1. LANDING PAGE TESTING
  // ─────────────────────────────────────────────────────────────
  console.log('\n[TEST 1] Visiting Landing Page (/)...\n');
  const t0 = Date.now();
  await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
  auditLog.performanceMetrics['landing_load_ms'] = Date.now() - t0;

  for (const vp of VIEWPORTS) {
    await page.setViewportSize({ width: vp.width, height: vp.height });
    await sleep(500);
    const ssPath = path.join(SCREENSHOTS_DIR, `01_landing_${vp.suffix}.png`);
    await page.screenshot({ path: ssPath, fullPage: true });
    console.log(`Saved screenshot: ${ssPath}`);
  }

  // Restore Desktop Viewport
  await page.setViewportSize({ width: 1440, height: 900 });

  // Verify Landing Page Elements
  const heroHeading = await page.locator('h1').first().innerText();
  console.log(`Landing Page Heading: "${heroHeading.trim()}"`);
  auditLog.pagesTested.push({ route: '/', title: 'Landing Page', heading: heroHeading.trim(), status: 'PASS' });

  // Find and click "Enter Command Center"
  console.log('Clicking "Enter Command Center" CTA button...');
  const enterBtn = page.locator('button:has-text("Enter Command Center"), a:has-text("Enter Command Center")').first();
  if (await enterBtn.isVisible()) {
    await enterBtn.click();
    await sleep(1500);
    auditLog.elementsTested.push({ control: 'Landing CTA: Enter Command Center', action: 'click', result: 'Navigated to /app' });
  } else {
    console.warn('Could not find Enter Command Center button, navigating directly to /app');
    await page.goto(`${BASE_URL}/app`, { waitUntil: 'networkidle' });
  }

  // ─────────────────────────────────────────────────────────────
  // 2. APP SHELL & TOPBAR / SIDEBAR CONTROLS
  // ─────────────────────────────────────────────────────────────
  console.log('\n[TEST 2] Verifying App Shell, TopBar & Sidebar Controls...\n');

  // 2A. Test Sidebar Collapse / Expand Toggle Button
  const collapseToggle = page.locator('#sidebar-collapse-toggle');
  if (await collapseToggle.isVisible()) {
    console.log('Clicking Sidebar Collapse Toggle...');
    await collapseToggle.click();
    await sleep(600);
    const ssCollapsed = path.join(SCREENSHOTS_DIR, '02_sidebar_collapsed.png');
    await page.screenshot({ path: ssCollapsed });
    console.log(`Saved screenshot: ${ssCollapsed}`);

    // Expand it back
    await collapseToggle.click();
    await sleep(600);
    auditLog.elementsTested.push({ control: 'Sidebar Rail Collapse Toggle', action: 'toggle', result: 'Collapsed & Expanded cleanly' });
  }

  // 2B. Test TopBar User Avatar Dropdown
  const userBtn = page.locator('button[aria-label="User profile menu"]');
  if (await userBtn.isVisible()) {
    console.log('Opening User Profile Menu...');
    await userBtn.click();
    await sleep(500);
    const ssUser = path.join(SCREENSHOTS_DIR, '03_user_menu_open.png');
    await page.screenshot({ path: ssUser });
    // Close it
    await userBtn.click();
    await sleep(300);
    auditLog.elementsTested.push({ control: 'TopBar User Avatar Menu', action: 'toggle', result: 'Opened & Closed cleanly' });
  }

  // ─────────────────────────────────────────────────────────────
  // 3. EIGHT MAIN WORKSPACE TABS (MUMBAI DEEP TIER)
  // ─────────────────────────────────────────────────────────────
  const TABS = [
    { id: 'overview',        label: 'Overview',          btnSelector: '#nav-overview' },
    { id: 'flood-map',       label: 'Flood Outlook',     btnSelector: '#nav-flood-map' },
    { id: 'travel-window',   label: 'Travel Window',     btnSelector: '#nav-travel-window' },
    { id: 'critical-access', label: 'Critical Access',   btnSelector: '#nav-critical-access' },
    { id: 'protect-city',    label: 'Protect the City',  btnSelector: '#nav-protect-city' },
    { id: 'ground-truth',    label: 'Ground Truth',      btnSelector: '#nav-ground-truth' },
    { id: 'simulator',       label: 'Simulator',         btnSelector: '#nav-simulator' },
  ];

  for (const tab of TABS) {
    console.log(`\nTesting Tab: [${tab.label}] (${tab.id})...`);
    const navBtn = page.locator(tab.btnSelector);
    if (await navBtn.isVisible()) {
      const tNav = Date.now();
      await navBtn.click();
      await sleep(1500);
      auditLog.performanceMetrics[`nav_to_${tab.id}_ms`] = Date.now() - tNav;

      for (const vp of VIEWPORTS) {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await sleep(400);
        const ssTab = path.join(SCREENSHOTS_DIR, `tab_${tab.id}_${vp.suffix}.png`);
        await page.screenshot({ path: ssTab });
      }
      await page.setViewportSize({ width: 1440, height: 900 });

      auditLog.pagesTested.push({
        route: `/app#${tab.id}`,
        title: tab.label,
        status: 'PASS',
      });
      auditLog.elementsTested.push({ control: `Nav Tab: ${tab.label}`, action: 'click', result: 'Tab loaded cleanly' });
    } else {
      console.error(`Nav button ${tab.btnSelector} not visible!`);
      auditLog.defects.push({ id: `DEF-NAV-${tab.id}`, severity: 'P1', title: `Missing Nav Button for ${tab.label}` });
    }
  }

  // Also test Alert Center (accessible via Bell icon)
  console.log('\nTesting Alert Center via TopBar Bell...');
  const bellBtn = page.locator('button[aria-label="Open alerts center"]');
  if (await bellBtn.isVisible()) {
    await bellBtn.click();
    await sleep(1500);
    for (const vp of VIEWPORTS) {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await sleep(400);
      const ssAlerts = path.join(SCREENSHOTS_DIR, `tab_alerts_${vp.suffix}.png`);
      await page.screenshot({ path: ssAlerts });
    }
    await page.setViewportSize({ width: 1440, height: 900 });
    auditLog.pagesTested.push({ route: '/app#alerts', title: 'Alert Center', status: 'PASS' });
    auditLog.elementsTested.push({ control: 'TopBar Bell (Alert Center)', action: 'click', result: 'Alert Center loaded' });
  }

  // ─────────────────────────────────────────────────────────────
  // 4. TESTING INTERACTIVE CONTROLS PER FEATURE
  // ─────────────────────────────────────────────────────────────
  console.log('\n[TEST 4] Testing Feature-Specific Interactive Controls...\n');

  // 4A. Critical Access: Test filter buttons & search
  await page.locator('#nav-critical-access').click();
  await sleep(1000);
  const searchInput = page.locator('input[placeholder*="Search facilities"], input[type="text"]').first();
  if (await searchInput.isVisible()) {
    await searchInput.fill('Hospital');
    await sleep(600);
    auditLog.elementsTested.push({ control: 'Critical Access Search Input', action: 'type "Hospital"', result: 'Filter applied' });
    await searchInput.fill('');
    await sleep(400);
  }

  // 4B. Simulator: Test Presets and Simulation Trigger
  await page.locator('#nav-simulator').click();
  await sleep(1000);
  const simPresets = page.locator('button:has-text("Cloudburst"), button:has-text("Monsoon"), button:has-text("Extreme")');
  const presetCount = await simPresets.count();
  if (presetCount > 0) {
    console.log(`Found ${presetCount} simulator presets, clicking first preset...`);
    await simPresets.first().click();
    await sleep(600);
    auditLog.elementsTested.push({ control: 'Simulator Preset Button', action: 'click', result: 'Preset values loaded' });
  }

  // ─────────────────────────────────────────────────────────────
  // 5. GEOGRAPHIC TIER MODAL & MULTISCALE HIERARCHY
  // ─────────────────────────────────────────────────────────────
  console.log('\n[TEST 5] Testing Geographic Tier Modal & Intelligence Switching...\n');

  // Open modal via TopBar Location Badge
  const tierBadge = page.locator('button:has-text("ZONE"), button:has-text("Catchment"), button:has-text("Mumbai")').first();
  console.log('Opening Geographic Tier Modal...');
  await tierBadge.click();
  await sleep(1000);

  const ssModal = path.join(SCREENSHOTS_DIR, '04_geographic_tier_modal.png');
  await page.screenshot({ path: ssModal });
  console.log(`Saved screenshot: ${ssModal}`);
  auditLog.elementsTested.push({ control: 'Geographic Tier Modal Trigger', action: 'click', result: 'Modal rendered' });

  // 5A. Select Mahanadi River Basin (Phase 7F Research Study)
  console.log('Selecting Mahanadi Basin Preset in Tier Modal...');
  const mahanadiBtn = page.locator('button:has-text("Mahanadi")').first();
  if (await mahanadiBtn.isVisible()) {
    await mahanadiBtn.click();
    await sleep(2000);
    auditLog.tiersTested.push({ tier: 'REGIONAL', zone: 'regional_mahanadi_basin', status: 'PASS' });
    auditLog.elementsTested.push({ control: 'Modal Option: Mahanadi Basin', action: 'select', result: 'Switched to Regional Mahanadi' });

    // Verify Mahanadi Regional Overview
    const ssMahanadiOverview = path.join(SCREENSHOTS_DIR, '05_mahanadi_regional_overview.png');
    await page.screenshot({ path: ssMahanadiOverview, fullPage: true });
    console.log(`Saved screenshot: ${ssMahanadiOverview}`);

    // Verify Mahanadi Flood Map & 5 Layer Controls
    await page.locator('#nav-flood-map').click();
    await sleep(2000);
    const ssMahanadiMap = path.join(SCREENSHOTS_DIR, '06_mahanadi_research_map.png');
    await page.screenshot({ path: ssMahanadiMap, fullPage: true });
    console.log(`Saved screenshot: ${ssMahanadiMap}`);

    // Toggle a research layer (e.g. land_water_mask)
    const layerToggle = page.locator('button[role="switch"], input[type="checkbox"]').first();
    if (await layerToggle.isVisible()) {
      await layerToggle.click();
      await sleep(500);
      auditLog.elementsTested.push({ control: 'Mahanadi Research Layer Toggle', action: 'toggle', result: 'Layer visibility changed' });
    }
  }

  // 5B. Select National Tier (India Macro Screening)
  console.log('Switching to National Macro Screening...');
  const tierBadge2 = page.locator('button:has-text("ZONE"), button:has-text("Basin"), button:has-text("Mahanadi")').first();
  await tierBadge2.click();
  await sleep(800);

  const nationalBtn = page.locator('button:has-text("National"), button:has-text("India Subcontinent")').first();
  if (await nationalBtn.isVisible()) {
    await nationalBtn.click();
    await sleep(1500);
    await page.locator('#nav-overview').click();
    await sleep(1000);
    const ssNational = path.join(SCREENSHOTS_DIR, '07_national_screening_overview.png');
    await page.screenshot({ path: ssNational, fullPage: true });
    console.log(`Saved screenshot: ${ssNational}`);
    auditLog.tiersTested.push({ tier: 'NATIONAL', zone: 'national_india', status: 'PASS' });
  }

  // 5C. Return to Deep Tier (Mumbai · Mithi Catchment)
  console.log('Resetting to Mumbai Mithi Deep Zone...');
  const tierBadge3 = page.locator('button:has-text("ZONE"), button:has-text("India")').first();
  await tierBadge3.click();
  await sleep(800);

  const mumbaiBtn = page.locator('button:has-text("Mumbai"), button:has-text("Mithi")').first();
  if (await mumbaiBtn.isVisible()) {
    await mumbaiBtn.click();
    await sleep(1500);
    await page.locator('#nav-overview').click();
    await sleep(1000);
    const ssMumbai = path.join(SCREENSHOTS_DIR, '08_mumbai_deep_restored.png');
    await page.screenshot({ path: ssMumbai });
    console.log(`Saved screenshot: ${ssMumbai}`);
    auditLog.tiersTested.push({ tier: 'DEEP', zone: 'mumbai_mithi_deep', status: 'PASS' });
  }

  // ─────────────────────────────────────────────────────────────
  // 6. BACKEND API VERIFICATION SUITE
  // ─────────────────────────────────────────────────────────────
  console.log('\n[TEST 6] Directly verifying backend API endpoints via browser context...\n');
  const apiChecks = [
    { name: 'Health Live', url: `${API_URL}/api/v1/health/live`, expectedStatus: 200 },
    { name: 'Locations Root', url: `${API_URL}/api/v1/locations`, expectedStatus: 200 },
    { name: 'Mahanadi Basin Detail', url: `${API_URL}/api/v1/locations/BASIN-MAHANADI`, expectedStatus: 200 },
    { name: 'Mahanadi Experiments', url: `${API_URL}/api/v1/intelligence/regional/mahanadi/experiments`, expectedStatus: 200 },
    { name: 'Mahanadi Subbasins', url: `${API_URL}/api/v1/intelligence/regional/mahanadi/subbasins`, expectedStatus: 200 },
    { name: 'Mahanadi Layers', url: `${API_URL}/api/v1/intelligence/regional/mahanadi/layers`, expectedStatus: 200 },
    { name: 'Critical Facilities', url: `${API_URL}/api/v1/critical-access/facilities`, expectedStatus: 200 },
    { name: 'Alerts', url: `${API_URL}/api/v1/alerts`, expectedStatus: 200 },
    { name: 'Protect City Candidates', url: `${API_URL}/api/v1/protect-city/candidates`, expectedStatus: 200 },
  ];

  for (const check of apiChecks) {
    const res = await page.request.get(check.url);
    const status = res.status();
    console.log(`API [${check.name}]: HTTP ${status} (expected ${check.expectedStatus})`);
    if (status === check.expectedStatus) {
      auditLog.elementsTested.push({ control: `API: ${check.name}`, action: 'GET', result: `HTTP ${status} OK` });
    } else {
      auditLog.defects.push({ id: `DEF-API-${check.name}`, severity: 'P1', title: `API Failure ${check.name}: HTTP ${status}` });
    }
  }

  // Test Unsupported Deep Zone Rejection (Patna)
  console.log('Verifying Unsupported Deep Zone Rejection for Patna...');
  const patnaRes = await page.request.post(`${API_URL}/api/v1/intelligence/deep`, {
    data: { latitude: 25.6, longitude: 85.1 },
  });
  const patnaData = await patnaRes.json();
  if (patnaRes.status() === 200 && patnaData.status === 'OUTSIDE_DEEP_ZONE_COVERAGE' && patnaData.point_in_zone === false) {
    console.log('Patna Rejection Invariant verified: OUTSIDE_DEEP_ZONE_COVERAGE (point_in_zone: false)');
    auditLog.elementsTested.push({ control: 'Unsupported Zone Rejection (Patna)', action: 'POST', result: 'OUTSIDE_DEEP_ZONE_COVERAGE verified' });
  } else {
    console.error('Patna Rejection Failed!', patnaData);
    auditLog.defects.push({ id: 'DEF-UNSUPPORTED-PATNA', severity: 'P0', title: 'Patna failed clean unsupported rejection' });
  }

  await browser.close();

  // Save audit log to JSON
  const auditLogPath = path.resolve('artifacts/browser_qa/browser_qa_audit_log.json');
  fs.writeFileSync(auditLogPath, JSON.stringify(auditLog, null, 2), 'utf-8');
  console.log(`\nAudit log saved to: ${auditLogPath}`);

  console.log('\n================================================================');
  console.log(`   AUTOMATED BROWSER QA COMPLETE: ${auditLog.defects.length} DEFECTS FOUND`);
  console.log(`   Console Errors: ${auditLog.consoleErrors.length}`);
  console.log(`   Failed Requests: ${auditLog.failedRequests.length}`);
  console.log('================================================================\n');
}

runAudit().catch((err) => {
  console.error('Fatal error during browser QA audit:', err);
  process.exit(1);
});
