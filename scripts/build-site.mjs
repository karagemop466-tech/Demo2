import { cpSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const root = process.cwd();
const siteRoot = join(root, "monitor");
const output = join(root, "dist");
const staticPages = [
  "index.html",
  "404.html",
  "executive-summary.html",
  "requirements.html",
  "methodology.html",
  "portfolio.html",
  "watchlist.html",
  "suggestions.html",
  "review.html",
  "sources.html",
];

rmSync(output, { recursive: true, force: true });
mkdirSync(output, { recursive: true });
for (const file of staticPages) cpSync(join(siteRoot, file), join(output, file));
for (const directory of ["assets", "categories"]) {
  cpSync(join(siteRoot, directory), join(output, directory), { recursive: true });
}

const htmlCount = readdirSync(output, { recursive: true }).filter((file) => String(file).endsWith(".html")).length;
console.log(`Built ${htmlCount} static HTML pages into dist/.`);
