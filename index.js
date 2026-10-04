import { readFile, readdir, stat } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// A bundled skill provider: it ships a `skills/` directory inside this bundle and
// serves every `<skill>/SKILL.md` to the host skill registry. No external
// dependencies — so the bundle installs cleanly as a profile bundle (the profile
// node_modules does not resolve the DSH runtime packages).

const PROVIDER_NAME = "pythongo-strategy-dev";
// Mirrors BUNDLED_SKILL_RANK (600) from @deepseek-ai/dsh-skill without importing it.
const BUNDLED_SKILL_RANK = 600;
const SKILL_NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export const inject = ["skills"];

export function apply(ctx, _config = {}) {
  const skillsDir = join(dirname(fileURLToPath(import.meta.url)), "skills");
  ctx.skills.registerProvider((_control) => new BundledSkillProvider(skillsDir));
}

class BundledSkillProvider {
  constructor(skillsDir) {
    this.name = PROVIDER_NAME;
    this.skillsDir = skillsDir;
  }

  async list(_options = {}) {
    const candidates = [];
    let entries;
    try {
      entries = await readdir(this.skillsDir, { withFileTypes: true });
    } catch {
      return candidates;
    }
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (!entry.isDirectory()) continue;
      const dir = join(this.skillsDir, entry.name);
      const skillPath = join(dir, "SKILL.md");
      let parsed;
      try {
        parsed = await parseSkillFile(skillPath);
      } catch {
        continue;
      }
      if (parsed === undefined) continue;
      candidates.push({
        name: parsed.name,
        description: parsed.description,
        ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
        invocation: parsed.invocation,
        provider: this.name,
        source: "bundled",
        rank: BUNDLED_SKILL_RANK,
        locator: { path: skillPath, directory: dir },
        resourceBase: { kind: "directory", path: dir },
        path: skillPath,
      });
    }
    return candidates;
  }

  async get(candidate, _options = {}) {
    const parsed = await parseSkillFile(candidate.locator.path);
    if (parsed === undefined) return undefined;
    return {
      name: parsed.name,
      description: parsed.description,
      ...(parsed.whenToUse !== undefined ? { whenToUse: parsed.whenToUse } : {}),
      invocation: parsed.invocation,
      source: "bundled",
      provider: this.name,
      resourceBase: { kind: "directory", path: candidate.locator.directory },
      path: candidate.locator.path,
      content: parsed.content,
    };
  }
}

// Minimal YAML frontmatter parser sufficient for the flat frontmatter used by
// this bundle's skill files (name / description / whenToUse / invocation flags).
async function parseSkillFile(path) {
  let raw;
  try {
    raw = await readFile(path, "utf8");
  } catch {
    return undefined;
  }
  const fm = parseFrontmatter(raw);
  if (fm === undefined) return undefined;
  const data = fm.data;
  const name = typeof data.name === "string" ? data.name.trim() : "";
  const description =
    typeof data.description === "string" ? data.description.trim() : "";
  if (!name || !description || !SKILL_NAME_RE.test(name)) return undefined;
  const whenToUse =
    typeof data.whenToUse === "string" && data.whenToUse.trim().length > 0
      ? data.whenToUse.trim()
      : undefined;
  const modelInvocable = !truthy(data["disable-model-invocation"]);
  const userInvocable =
    data["user-invocable"] === undefined ? true : truthy(data["user-invocable"]);
  return {
    name,
    description,
    whenToUse,
    invocation: { modelInvocable, userInvocable },
    content: fm.body.trim(),
  };
}

function parseFrontmatter(raw) {
  const firstEnd = raw.indexOf("\n");
  if (firstEnd < 0) return undefined;
  if (raw.slice(0, firstEnd).replace(/\r$/, "") !== "---") return undefined;
  const start = firstEnd + 1;
  let lineStart = start;
  while (lineStart <= raw.length) {
    const next = raw.indexOf("\n", lineStart);
    const lineEnd = next < 0 ? raw.length : next;
    if (raw.slice(lineStart, lineEnd).replace(/\r$/, "") === "---") {
      const bodyStart = next < 0 ? raw.length : next + 1;
      return {
        data: parseFlatYaml(raw.slice(start, lineStart)),
        body: raw.slice(bodyStart),
      };
    }
    if (next < 0) return undefined;
    lineStart = next + 1;
  }
  return undefined;
}

function parseFlatYaml(text) {
  const out = {};
  for (const rawLine of text.split("\n")) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const idx = line.indexOf(":");
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    out[key] = value;
  }
  return out;
}

function truthy(value) {
  if (typeof value === "boolean") return value;
  if (typeof value === "string")
    return ["true", "yes", "on", "1"].includes(value.toLowerCase());
  if (value === 1) return true;
  return false;
}
