import assert from 'node:assert/strict';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {chromium} from 'playwright';

const target = process.env.BROWSER_TARGET || 'preview';
const base = target === 'live'
  ? 'https://sagarchhatrala.github.io/purpose-trace/'
  : 'http://127.0.0.1:8765/';
const output = process.env.BROWSER_OUTPUT || 'browser-evidence';
await mkdir(output, {recursive: true});
const browser = await chromium.launch();
const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
await context.grantPermissions(['clipboard-read', 'clipboard-write'], {origin: new URL(base).origin});
const page = await context.newPage();
const errors = [];
const checks = [];
page.on('pageerror', error => errors.push(error.message));
const check = async (name, action) => {
  await action();
  checks.push(name);
  console.log(`PASS: ${name}`);
};
const text = selector => page.locator(selector).textContent();
try {
  await check('page and published assets match this checkout', async () => {
    const response = await page.goto(base, {waitUntil: 'networkidle'});
    assert.equal(response.status(), 200);
    for (const file of ['index.html', 'styles.css', 'app.js', 'evidence.json', 'mark.svg', 'project.json', 'llms.txt']) {
      const asset = await context.request.get(new URL(file, base).href);
      assert.equal(asset.status(), 200, file);
      assert.deepEqual(await asset.body(), await readFile(new URL(`../../site/${file}`, import.meta.url)), file);
    }
  });
  await check('keyboard skip link and all three routing strategies', async () => {
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
    await page.keyboard.press('Enter');
    assert.equal(new URL(page.url()).hash, '#main');
    const cases = [
      ['clean', 'CONSISTENT', 'billing-east', 'Standard support'],
      ['mismatch', 'INCONCLUSIVE', 'billing-west', 'Priority support'],
      ['leak', 'VIOLATION', 'billing-west', 'Standard support']
    ];
    for (const [scenario, status, queue, input] of cases) {
      await page.locator(`[data-scenario=${scenario}]`).click();
      assert.equal(await text('#lab-status'), status);
      assert.equal(await text('#output-b'), queue);
      assert.equal(await text('#input-b'), input);
      assert.equal(await page.locator('[data-scenario][aria-pressed=true]').count(), 1);
    }
    await page.locator('[data-scenario=leak]').focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').getAttribute('data-scenario'), 'clean');
    await page.keyboard.press('Space');
    assert.equal(await text('#lab-status'), 'CONSISTENT');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    assert.equal(await text('#lab-status'), 'INCONCLUSIVE');
  });
  await check('recorded report and interpretation boundaries', async () => {
    await page.locator('#sample-report').click();
    await page.locator('#report-content').waitFor({state: 'visible'});
    assert.equal(await text('#report-status'), 'VIOLATION');
    assert.equal(await page.locator('.group-row').count(), 3);
    await page.locator('.boundaries summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('.boundaries').getAttribute('open'), '');
    assert.ok(await page.locator('#report-limitations li').count() > 0);
  });
  await check('local JSON import stays local and renders text safely', async () => {
    const report = JSON.parse(await readFile(new URL('../../site/evidence.json', import.meta.url)));
    report.policy.name = 'Local import <img src=x onerror=alert(1)>';
    const requests = [];
    const observe = request => requests.push(request.url());
    page.on('request', observe);
    await page.locator('#report-file').setInputFiles({name: 'report.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify(report))});
    await page.waitForFunction(() => document.querySelector('#report-message').textContent.startsWith('Your report is open.'));
    page.off('request', observe);
    assert.equal(requests.length, 0, 'local import made a network request');
    assert.ok((await text('#report-policy')).includes(report.policy.name));
    assert.equal(await page.locator('#report-policy img').count(), 0);
  });
  await check('malformed JSON and invalid report schema fail visibly', async () => {
    for (const [name, data, expected] of [
      ['broken.json', '{', 'The selected file is not valid JSON.'],
      ['wrong.json', '{}', 'This is not a supported PurposeTrace version 1 report.']
    ]) {
      await page.locator('#report-file').setInputFiles({name, mimeType: 'application/json', buffer: Buffer.from(data)});
      await page.waitForFunction(expected => document.querySelector('#report-message').textContent === expected, expected);
      assert.equal(await page.locator('#report-message').getAttribute('data-error'), 'true');
      assert.equal(await page.locator('#report-content').isVisible(), false);
    }
    await page.locator('#sample-report').click();
    await page.locator('#report-content').waitFor({state: 'visible'});
  });
  await check('clipboard copies the exact quickstart', async () => {
    await page.locator('#copy-command').click();
    await page.waitForFunction(() => document.querySelector('#copy-status').textContent.startsWith('Commands copied.'));
    assert.equal(await page.evaluate(() => navigator.clipboard.readText()), await text('#quickstart'));
  });
  await check('desktop and narrow layouts keep controls within the viewport', async () => {
    for (const width of [1440, 768, 375, 320]) {
      await page.setViewportSize({width, height: 1000});
      const layout = await page.evaluate(() => ({width: window.innerWidth, scroll: document.documentElement.scrollWidth}));
      assert.ok(layout.scroll <= layout.width, `horizontal overflow at ${width}: ${layout.scroll}`);
      for (const selector of ['[data-scenario=leak]', '[data-scenario=clean]', '[data-scenario=mismatch]', '#sample-report', '#copy-command', 'label[for=report-file]']) {
        const box = await page.locator(selector).boundingBox();
        assert.ok(box && box.x >= 0 && box.x + box.width <= width + 1, `${selector} outside ${width}px viewport`);
      }
      await page.screenshot({path: `${output}/${target}-${width}.png`, fullPage: true});
    }
  });
  if (target === 'live') {
    await check('homepage and existing project routes remain available', async () => {
      for (const route of ['/', '/agent-circuit-breaker/', '/horizon-agent-containment/']) {
        const response = await context.request.get(`https://sagarchhatrala.github.io${route}`);
        assert.equal(response.status(), 200, route);
        assert.match(await response.text(), /<html/i);
      }
    });
  }
  assert.deepEqual(errors, [], 'uncaught browser errors');
} finally {
  await writeFile(`${output}/${target}-results.json`, JSON.stringify({target, base, checks, errors}, null, 2));
  await browser.close();
}
