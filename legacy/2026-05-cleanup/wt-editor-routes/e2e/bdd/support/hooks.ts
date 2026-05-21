import {
  Before,
  After,
  BeforeAll,
  AfterAll,
  Status,
} from "@cucumber/cucumber";
import { PlaywrightWorld } from "./world";
import * as fs from "fs";
import * as path from "path";

const REPORTS_DIR = path.join(process.cwd(), "reports", "bdd");
const SCREENSHOTS_DIR = path.join(REPORTS_DIR, "screenshots");

BeforeAll(async function () {
  fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
});

Before(async function (this: PlaywrightWorld) {
  await this.init();
});

After(async function (this: PlaywrightWorld, scenario) {
  if (scenario.result?.status === Status.FAILED) {
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
      // screenshot/heal failure should not mask the original error
    }
  }

  await this.cleanup();
});

AfterAll(async function () {
  // final cleanup
});
