import chalk from "chalk";

let counters = { fail: 0, warn: 0, info: 0, ok: 0 };

export function resetCounters() {
  counters = { fail: 0, warn: 0, info: 0, ok: 0 };
}

export function getCounters() {
  return { ...counters };
}

export function fail(message, context = null) {
  counters.fail++;
  const ctx = context ? chalk.dim(` (${context})`) : "";
  console.error(`${chalk.red("✗ FAIL")} ${message}${ctx}`);
}

export function warn(message, context = null) {
  counters.warn++;
  const ctx = context ? chalk.dim(` (${context})`) : "";
  console.warn(`${chalk.yellow("⚠ WARN")} ${message}${ctx}`);
}

export function info(message, context = null) {
  counters.info++;
  const ctx = context ? chalk.dim(` (${context})`) : "";
  console.log(`${chalk.blue("ℹ INFO")} ${message}${ctx}`);
}

export function ok(message, context = null) {
  counters.ok++;
  const ctx = context ? chalk.dim(` (${context})`) : "";
  console.log(`${chalk.green("✓")}  ${message}${ctx}`);
}

export function section(title) {
  console.log("");
  console.log(chalk.bold.cyan(`── ${title} ` + "─".repeat(Math.max(0, 60 - title.length))));
}

export function summary() {
  console.log("");
  const { fail: f, warn: w, info: i, ok: o } = counters;
  console.log(
    chalk.bold("Özet: ") +
      chalk.green(`${o} ok`) +
      "  " +
      (f > 0 ? chalk.red(`${f} fail`) : chalk.dim(`${f} fail`)) +
      "  " +
      (w > 0 ? chalk.yellow(`${w} warn`) : chalk.dim(`${w} warn`)) +
      "  " +
      chalk.dim(`${i} info`),
  );
}
