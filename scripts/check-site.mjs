import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { dirname, extname, join, resolve, sep } from "node:path";

const inputRoot = resolve(process.cwd(), process.argv[2] ?? ".");
const root = inputRoot;
const errors = [];
const officialHosts = [
  "docs.kalshi.com",
  "external-api.demo.kalshi.co",
  "external-api-ws.demo.kalshi.co",
  "demo-api.kalshi.co",
  "demo.kalshi.co",
  "docs.github.com",
  "github.com",
];

function walk(directory) {
  const found = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    if ([".git", "node_modules", "dist"].includes(entry.name)) continue;
    const path = join(directory, entry.name);
    if (entry.isDirectory()) found.push(...walk(path));
    else found.push(path);
  }
  return found;
}

function isExternal(value) {
  return /^(?:https?:|mailto:|tel:|data:|javascript:)/i.test(value);
}

const htmlIdCache = new Map();

function htmlIds(path) {
  if (htmlIdCache.has(path)) return htmlIdCache.get(path);
  if (extname(path).toLowerCase() !== ".html") return null;
  const content = readFileSync(path, "utf8");
  const ids = new Set([...content.matchAll(/\bid=["']([^"']+)["']/gi)].map((match) => match[1]));
  htmlIdCache.set(path, ids);
  return ids;
}

function resolveLocalReference(pagePath, reference) {
  const withoutSuffix = reference.split(/[?#]/, 1)[0];
  if (!withoutSuffix) return pagePath;
  let decoded;
  try { decoded = decodeURIComponent(withoutSuffix); } catch { decoded = withoutSuffix; }
  const candidate = decoded.startsWith("/")
    ? join(root, decoded.slice(1))
    : resolve(dirname(pagePath), decoded);
  if (candidate !== root && !candidate.startsWith(`${root}${sep}`)) return null;
  if (existsSync(candidate)) {
    if (statSync(candidate).isDirectory()) {
      const indexPath = join(candidate, "index.html");
      return existsSync(indexPath) ? indexPath : null;
    }
    return candidate;
  }
  if (!extname(candidate)) {
    const indexPath = join(candidate, "index.html");
    if (existsSync(indexPath)) return indexPath;
  }
  return null;
}

const files = walk(root);
const htmlFiles = files.filter((path) => extname(path).toLowerCase() === ".html");
if (htmlFiles.length === 0) errors.push(`No HTML files found under ${root}`);

for (const pagePath of htmlFiles) {
  const html = readFileSync(pagePath, "utf8");
  const relativePage = pagePath.slice(root.length + 1).split(sep).join("/");
  const ids = new Set();

  for (const match of html.matchAll(/\bid=["']([^"']+)["']/gi)) {
    if (ids.has(match[1])) errors.push(`${relativePage}: duplicate id "${match[1]}"`);
    ids.add(match[1]);
  }
  htmlIdCache.set(pagePath, ids);

  for (const match of html.matchAll(/\b(href|src)=["']([^"']+)["']/gi)) {
    const [, attribute, reference] = match;
    if (isExternal(reference)) continue;
    const target = resolveLocalReference(pagePath, reference);
    if (!target) {
      errors.push(`${relativePage}: broken local ${attribute}="${reference}"`);
      continue;
    }
    const hashIndex = reference.indexOf("#");
    if (hashIndex >= 0 && hashIndex < reference.length - 1 && extname(target).toLowerCase() === ".html") {
      let fragment;
      try { fragment = decodeURIComponent(reference.slice(hashIndex + 1).split("?", 1)[0]); } catch { fragment = reference.slice(hashIndex + 1).split("?", 1)[0]; }
      if (fragment && !htmlIds(target)?.has(fragment)) errors.push(`${relativePage}: missing local fragment "${reference.slice(hashIndex)}"`);
    }
  }

  for (const anchor of html.matchAll(/<a\b([^>]*)>/gi)) {
    const attributes = anchor[1];
    if (/\btarget=["']_blank["']/i.test(attributes) && !/\brel=["'][^"']*noopener[^"']*["']/i.test(attributes)) {
      errors.push(`${relativePage}: target="_blank" anchor is missing rel="noopener"`);
    }
  }

  for (const tableBody of html.matchAll(/<tbody\b[^>]*>([\s\S]*?)<\/tbody>/gi)) {
    for (const row of tableBody[1].matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)) {
      const rowMarkup = row[1];
      const hasOfficialSource = officialHosts.some((host) => new RegExp(`https?:\\/\\/${host.replaceAll(".", "\\.")}\\/`, "i").test(rowMarkup));
      if (!hasOfficialSource) errors.push(`${relativePage}: table row is missing an official source link`);
    }
  }

  if (/\bon[a-z]+\s*=/i.test(html)) errors.push(`${relativePage}: inline event handler found`);
}

const secretPatterns = [
  /-----BEGIN (?:RSA )?PRIVATE KEY-----/,
  /KALSHI-ACCESS-SIGNATURE\s*[:=]\s*["'][A-Za-z0-9+/=]{32,}["']/,
];
for (const path of files.filter((file) => /\.(?:html|js|mjs|json|md|ya?ml)$/i.test(file))) {
  const content = readFileSync(path, "utf8");
  for (const pattern of secretPatterns) {
    if (pattern.test(content)) errors.push(`${path.slice(root.length + 1)}: possible credential material found`);
  }
}

if (errors.length) {
  console.error(`Site check failed with ${errors.length} issue(s):`);
  for (const error of errors) console.error(`- ${error}`);
  process.exitCode = 1;
} else {
  console.log(`Site check passed: ${htmlFiles.length} HTML pages, local references resolved, table rows source-linked, no duplicate IDs or inline handlers.`);
}
