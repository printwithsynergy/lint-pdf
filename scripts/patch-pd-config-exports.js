/**
 * Patch @thinkneverland/pixie-dust-config exports field.
 *
 * The package only declares an ESM "import" condition, but Next.js webpack
 * resolves some paths via CJS require(). Adding "require" and "default"
 * conditions fixes "Package path . is not exported" build errors.
 *
 * This is an upstream issue — remove once pixie-dust-config ships a CJS
 * export or a "default" condition in its exports map.
 */
const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

// Find all copies of pixie-dust-config in node_modules
const output = execSync(
  'find node_modules -path "*/pixie-dust-config/package.json" -not -path "*/node_modules/.pnpm/node_modules/*" 2>/dev/null || true',
  { encoding: "utf-8", cwd: path.resolve(__dirname, "..") }
).trim();

if (!output) {
  process.exit(0);
}

let patched = 0;
for (const pkgPath of output.split("\n").filter(Boolean)) {
  const fullPath = path.resolve(__dirname, "..", pkgPath);
  try {
    const pkg = JSON.parse(fs.readFileSync(fullPath, "utf-8"));
    const exp = pkg.exports?.["."];
    if (exp && exp.import && !exp.default) {
      exp.require = exp.import;
      exp.default = exp.import;
      fs.writeFileSync(fullPath, JSON.stringify(pkg, null, 2) + "\n");
      patched++;
    }
  } catch {
    // skip
  }
}

if (patched > 0) {
  console.log(`Patched ${patched} pixie-dust-config package(s) with CJS export conditions.`);
}
