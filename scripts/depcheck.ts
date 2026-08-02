/**
 * Dependency validation: every package imported by the source must be declared
 * in package.json. Catches phantom dependencies that only work because
 * something else happened to hoist them into node_modules.
 *
 * Prints one JSON object for the verification framework.
 */
import fs from "node:fs";
import path from "node:path";
import { builtinModules } from "node:module";

const ROOT = process.cwd();
const SCAN_DIRS = ["src", "tests", "scripts"];
const BUILTINS = new Set([...builtinModules, ...builtinModules.map((m) => `node:${m}`)]);
/** Path aliases resolved by tsconfig/vite rather than by node_modules. */
const ALIASES = ["@core/"];

interface PackageJson {
  dependencies?: Record<string, string>;
  devDependencies?: Record<string, string>;
}

function walk(dir: string, out: string[] = []): string[] {
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "node_modules" || entry.name.startsWith(".")) continue;
      walk(full, out);
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

/** Package name from a specifier: `@scope/pkg/sub` → `@scope/pkg`, `pkg/sub` → `pkg`. */
function packageName(specifier: string): string {
  const parts = specifier.split("/");
  return specifier.startsWith("@") ? parts.slice(0, 2).join("/") : parts[0];
}

function specifiers(source: string): string[] {
  const found = new Set<string>();
  const patterns = [
    /\bfrom\s+["']([^"']+)["']/g,
    /\bimport\s+["']([^"']+)["']/g,
    /\brequire\(\s*["']([^"']+)["']\s*\)/g,
    /\bimport\(\s*["']([^"']+)["']\s*\)/g,
  ];
  for (const pattern of patterns) {
    let match = pattern.exec(source);
    while (match !== null) {
      found.add(match[1]);
      match = pattern.exec(source);
    }
  }
  return [...found];
}

function main(): number {
  const pkg = JSON.parse(
    fs.readFileSync(path.join(ROOT, "package.json"), "utf8"),
  ) as PackageJson;
  const declared = new Set([
    ...Object.keys(pkg.dependencies ?? {}),
    ...Object.keys(pkg.devDependencies ?? {}),
  ]);

  const files = SCAN_DIRS.flatMap((dir) => walk(path.join(ROOT, dir)));
  const undeclared = new Map<string, string[]>();
  let imports = 0;

  for (const file of files) {
    const source = fs.readFileSync(file, "utf8");
    for (const specifier of specifiers(source)) {
      imports += 1;
      if (specifier.startsWith(".") || specifier.startsWith("/")) continue;
      if (BUILTINS.has(specifier) || BUILTINS.has(packageName(specifier))) continue;
      if (ALIASES.some((alias) => specifier.startsWith(alias))) continue;
      const name = packageName(specifier);
      if (declared.has(name)) continue;
      const seen = undeclared.get(name) ?? [];
      seen.push(path.relative(ROOT, file));
      undeclared.set(name, seen);
    }
  }

  const failures = [...undeclared.entries()].map(
    ([name, where]) => `${name} imported by ${where.slice(0, 3).join(", ")} but not declared`,
  );

  console.log(
    JSON.stringify({
      status: failures.length ? "fail" : "pass",
      gate: "deps.declared",
      metrics: {
        files_scanned: files.length,
        imports_scanned: imports,
        declared_packages: declared.size,
        undeclared: undeclared.size,
      },
      failures,
    }),
  );
  return failures.length ? 1 : 0;
}

process.exit(main());
