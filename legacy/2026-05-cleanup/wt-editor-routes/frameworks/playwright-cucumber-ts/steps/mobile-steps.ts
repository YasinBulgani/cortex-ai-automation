/**
 * Mobile Step Definitions
 *
 * Mobil DSL cümlecikleri için Playwright mobile emulation üzerine step'ler.
 * Visium Farm sayfası bu step'leri içeren feature'lara doğal entegre çalışır.
 *
 * Notlar:
 *  - Playwright mobile emulation (devices.iPhone 14 Pro, Pixel 7 vb.) üzerinde
 *    çalışır. Gerçek cihaz / Appium entegrasyonu sonraki fazda.
 *  - Sol-sağ / yukarı-aşağı "swipe" jestleri viewport merkezinden yapılır.
 *  - `pinch` Playwright'ın native API'sinde yok — emulate ediyoruz
 *    (`page.mouse.wheel`).
 *  - `set_network` için `context.route` kullanıyoruz (offline moduna gerçek
 *    intercept).
 */

import { Given, Then, When } from '@cucumber/cucumber';
import { expect } from '@playwright/test';

function logger(ctx: any) {
  return ctx.logger ?? console;
}

/** Locator çözücü — 'role:button:login', 'text:Giriş', 'css:.login' veya düz CSS */
function resolveLocator(page: any, selector: string) {
  if (!selector) throw new Error('selector boş');
  if (selector.startsWith('role:')) {
    const [, role, name] = selector.split(':');
    return page.getByRole(role, { name });
  }
  if (selector.startsWith('text:')) {
    return page.getByText(selector.slice(5), { exact: false });
  }
  if (selector.startsWith('label:')) {
    return page.getByLabel(selector.slice(6));
  }
  if (selector.startsWith('css:')) {
    return page.locator(selector.slice(4));
  }
  return page.locator(selector);
}

// ── Gesture: tap / long press / swipe / pinch ─────────────────────────────

When('I tap on {string}', async function (this: any, selector: string) {
  logger(this).debug(`[mobile] tap: ${selector}`);
  const el = resolveLocator(this.page, selector);
  await el.waitFor({ state: 'visible', timeout: 10_000 });
  await el.tap();
});

When(
  'I long press on {string}',
  async function (this: any, selector: string) {
    logger(this).debug(`[mobile] long press: ${selector}`);
    const el = resolveLocator(this.page, selector);
    await el.waitFor({ state: 'visible', timeout: 10_000 });
    const box = await el.boundingBox();
    if (!box) throw new Error(`Element kutusu alınamadı: ${selector}`);
    const x = box.x + box.width / 2;
    const y = box.y + box.height / 2;
    await this.page.mouse.move(x, y);
    await this.page.mouse.down();
    // 800ms default → DSL'de parameter ile değişir, burada fixed yakalama
    await this.page.waitForTimeout(800);
    await this.page.mouse.up();
  },
);

When(
  'I swipe {word}',
  async function (this: any, direction: string) {
    logger(this).debug(`[mobile] swipe: ${direction}`);
    const vp = this.page.viewportSize();
    if (!vp) throw new Error('viewport boyutu yok');
    const cx = Math.floor(vp.width / 2);
    const cy = Math.floor(vp.height / 2);
    const dist = Math.min(vp.width, vp.height) * 0.4;
    const delta: Record<string, [number, number]> = {
      up: [0, -dist],
      down: [0, dist],
      left: [-dist, 0],
      right: [dist, 0],
    };
    const d = delta[direction.toLowerCase()];
    if (!d) throw new Error(`bilinmeyen yön: ${direction}`);

    await this.page.mouse.move(cx, cy);
    await this.page.mouse.down();
    const steps = 12;
    for (let i = 1; i <= steps; i++) {
      await this.page.mouse.move(
        cx + (d[0] * i) / steps,
        cy + (d[1] * i) / steps,
      );
    }
    await this.page.mouse.up();
  },
);

When(
  'I scroll until {string} is visible',
  async function (this: any, text: string) {
    logger(this).debug(`[mobile] scroll until: ${text}`);
    const locator = this.page.getByText(text, { exact: false });
    const maxScrolls = 10;
    for (let i = 0; i < maxScrolls; i++) {
      if (await locator.isVisible().catch(() => false)) return;
      await this.page.mouse.wheel(0, 400);
      await this.page.waitForTimeout(200);
    }
    throw new Error(`metin ${maxScrolls} scroll'da görünmedi: "${text}"`);
  },
);

When(
  'I pinch to zoom by {float}',
  async function (this: any, factor: number) {
    logger(this).debug(`[mobile] pinch zoom: ${factor}`);
    // Playwright'ta native pinch yok; wheel + Ctrl = browser zoom
    const vp = this.page.viewportSize();
    if (!vp) return;
    await this.page.mouse.move(vp.width / 2, vp.height / 2);
    const deltaY = factor > 1 ? -100 * (factor - 1) : 100 * (1 - factor);
    await this.page.keyboard.down('Control');
    await this.page.mouse.wheel(0, deltaY);
    await this.page.keyboard.up('Control');
  },
);

// ── Device ─────────────────────────────────────────────────────────────────

When(
  'I rotate the device to {word}',
  async function (this: any, orientation: string) {
    logger(this).debug(`[mobile] rotate: ${orientation}`);
    const vp = this.page.viewportSize();
    if (!vp) return;
    const next =
      orientation.toLowerCase() === 'landscape'
        ? { width: Math.max(vp.width, vp.height), height: Math.min(vp.width, vp.height) }
        : { width: Math.min(vp.width, vp.height), height: Math.max(vp.width, vp.height) };
    await this.page.setViewportSize(next);
  },
);

When(
  'I press the {word} key',
  async function (this: any, key: string) {
    logger(this).debug(`[mobile] hardware key: ${key}`);
    const map: Record<string, () => Promise<void>> = {
      back: () => this.page.goBack(),
      home: () => this.page.goto('/'),
      menu: () => this.page.keyboard.press('F10'),
      volume_up: async () => { /* emulate yok */ },
      volume_down: async () => { /* emulate yok */ },
      power: async () => { /* emulate yok */ },
    };
    const fn = map[key.toLowerCase()];
    if (!fn) throw new Error(`desteklenmeyen tuş: ${key}`);
    await fn();
  },
);

When('I go back', async function (this: any) {
  logger(this).debug('[mobile] go back');
  await this.page.goBack();
});

// ── App ────────────────────────────────────────────────────────────────────

Given(
  'I launch the app {string}',
  async function (this: any, pkg: string) {
    logger(this).info(`[mobile] launch app: ${pkg} (emulation — goto /)`);
    // Mobile emulation'da uygulama açmak = ana URL'e git
    const baseUrl = process.env.BASE_URL || this.parameters?.baseUrl || '/';
    await this.page.goto(baseUrl, { waitUntil: 'networkidle' });
  },
);

Given(
  'I install the app {string}',
  async function (this: any, pkg: string) {
    logger(this).info(`[mobile] install app: ${pkg} (no-op in emulation)`);
    // Playwright emulation'da install adımı yok; gerçek cihaz için Appium ekleriz.
  },
);

// ── Network ────────────────────────────────────────────────────────────────

Given(
  'I set the network to {word}',
  async function (this: any, mode: string) {
    logger(this).info(`[mobile] set network: ${mode}`);
    const ctx = this.page.context();
    if (mode === 'offline') {
      await ctx.setOffline(true);
      return;
    }
    await ctx.setOffline(false);
    // Throttling için Playwright'ın native API'si sınırlı; CDP kullanılabilir
    // ama emulation modunda bunu basit tutuyoruz.
  },
);

// ── Permission ─────────────────────────────────────────────────────────────

Given(
  'I grant the {word} permission',
  async function (this: any, permission: string) {
    logger(this).info(`[mobile] grant permission: ${permission}`);
    const map: Record<string, string> = {
      camera: 'camera',
      microphone: 'microphone',
      location: 'geolocation',
      notifications: 'notifications',
      contacts: 'clipboard-read',
    };
    const pw = map[permission.toLowerCase()];
    if (!pw) {
      logger(this).warn(`bilinmeyen izin: ${permission} — atlandı`);
      return;
    }
    await this.page.context().grantPermissions([pw]);
  },
);

// ── Context (webview) ──────────────────────────────────────────────────────

When('I switch to webview', async function (this: any) {
  logger(this).debug('[mobile] switch to webview (emulation: no-op)');
  // Mobile emulation hep webview gibi davranır; gerçek cihaz + Appium'da
  // context switch burada yapılır.
});

// ── Assert ─────────────────────────────────────────────────────────────────

Then(
  'the element {string} should be on screen',
  async function (this: any, selector: string) {
    logger(this).debug(`[mobile] assert on screen: ${selector}`);
    const el = resolveLocator(this.page, selector);
    await expect(el).toBeVisible({ timeout: 10_000 });
  },
);

// ── Screenshot ─────────────────────────────────────────────────────────────

When('I take a mobile screenshot', async function (this: any) {
  const name = `mobile-${Date.now()}.png`;
  const out = await this.page.screenshot({ fullPage: false });
  if (this.attach) {
    await this.attach(out, 'image/png');
  }
  logger(this).info(`[mobile] screenshot: ${name}`);
});
