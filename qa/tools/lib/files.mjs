import fg from "fast-glob";
import matter from "gray-matter";
import yaml from "js-yaml";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const QA_ROOT = path.resolve(fileURLToPath(import.meta.url), "../../..");
export const REPO_ROOT = path.resolve(QA_ROOT, "..");

export async function listMarkdown(globPattern, { cwd = QA_ROOT } = {}) {
  return fg(globPattern, { cwd, absolute: true, dot: false });
}

export async function listYaml(globPattern, { cwd = QA_ROOT } = {}) {
  return fg(globPattern, { cwd, absolute: true, dot: false });
}

const YAML_OPTS = { schema: yaml.JSON_SCHEMA };

export async function readMarkdownFrontmatter(filePath) {
  const raw = await readFile(filePath, "utf8");
  const parsed = matter(raw, {
    engines: {
      yaml: {
        parse: (input) => yaml.load(input, YAML_OPTS),
        stringify: (input) => yaml.dump(input),
      },
    },
  });
  return { data: parsed.data, content: parsed.content, raw };
}

export async function readYamlFile(filePath) {
  const raw = await readFile(filePath, "utf8");
  const data = yaml.load(raw, { filename: filePath, ...YAML_OPTS });
  return { data, raw };
}

export async function loadAllTestCases() {
  const files = await listMarkdown("cases/**/TC-*.md");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readMarkdownFrontmatter(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export async function loadAllSuites() {
  const files = await listYaml("cases/**/_suite.yml");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readYamlFile(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export async function loadAllPreConditions() {
  const files = await listMarkdown("shared/pre-conditions/PRE-*.md");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readMarkdownFrontmatter(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export async function loadAllRequirements() {
  const files = await listMarkdown("requirements/REQ-*.md");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readMarkdownFrontmatter(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export async function loadAllPlans() {
  const files = await listYaml("plans/*.yml");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readYamlFile(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export async function loadAllRuns() {
  const files = await listYaml("runs/**/TR-*.yml");
  const out = [];
  for (const file of files) {
    try {
      const { data } = await readYamlFile(file);
      out.push({ file, data });
    } catch (err) {
      out.push({ file, data: null, error: err.message });
    }
  }
  return out;
}

export function relativeToRepo(absolutePath) {
  return path.relative(REPO_ROOT, absolutePath);
}

export function relativeToQa(absolutePath) {
  return path.relative(QA_ROOT, absolutePath);
}
