import {
  Before,
  After,
  AfterStep,
  BeforeAll,
  AfterAll,
  setDefaultTimeout,
  Status,
} from "@cucumber/cucumber";
import { PlaywrightWorld } from "./world";
import * as fs from "fs";
import * as path from "path";

// Playwright operasyonları 30 sn timeout; CI'da yavaş olabilir
setDefaultTimeout(30_000);

const REPORTS_DIR = path.join(process.cwd(), "reports", "bdd");
const SCREENSHOTS_DIR = path.join(REPORTS_DIR, "screenshots");

BeforeAll(async function () {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
});

Before(async function (this: PlaywrightWorld) {
  await this.init();
});

After(async function (this: PlaywrightWorld, scenario) {
  const failed = scenario.result?.status === Status.FAILED;

  if (failed) {
    // Ekran görüntüsü — hata orijinalini maskelememeli
    try {
      const screenshot = await this.page.screenshot({ fullPage: true });
      const filename = scenario.pickle.name
        .replace(/[^a-zA-Z0-9]/g, "_")
        .toLowerCase();
      const screenshotPath = path.join(
        SCREENSHOTS_DIR,
        `${filename}_${Date.now()}.png`,
      );
      fs.writeFileSync(screenshotPath, screenshot);
      this.attach(screenshot, "image/png");
    } catch {
      // screenshot failure — orijinal hatayı maskeleme
    }

    // Self-healing denemesi
    try {
      const healResult = await this.selfHealing.attemptHeal(
        scenario.pickle.name,
      );
      if (healResult.healed) {
        this.attach(
          `Self-healing applied: ${healResult.summary}`,
          "text/plain",
        );
      }
    } catch {
      // healing failure — orijinal hatayı maskeleme
    }
  }

  // Cleanup — her zaman çalışır; bireysel hatalar fırlatılmaz
  await this.cleanup();
});

AfterAll(async function () {
  // final cleanup placeholder — gerekirse suite-seviye kaynak serbest bırakma
});
