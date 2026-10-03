import { createRequire } from "node:module";
import {
  mkdtempSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, relative } from "node:path";
import { ESLint } from "eslint";
import { afterAll, describe, expect, it } from "vitest";

const pluginRequire = createRequire(
  require.resolve("@next/eslint-plugin-next/package.json"),
);
const plugin = pluginRequire("./dist/index.js");
const { getRootDirs } = pluginRequire("./dist/utils/get-root-dirs.js");
const adapter = pluginRequire("fast-glob");
const fixture = mkdtempSync(join(tmpdir(), "sm-next-roots-"));
for (const dir of [
  "alpha/pages",
  "alpha/app/nested",
  "beta/pages",
  ".hidden/pages",
]) {
  mkdirSync(join(fixture, dir), { recursive: true });
}
writeFileSync(
  join(fixture, "alpha/pages/about.tsx"),
  "export default function About() { return null; }",
);
writeFileSync(join(fixture, "file.txt"), "not a directory");
afterAll(() => rmSync(fixture, { recursive: true, force: true }));

const roots = (rootDir?: unknown) =>
  getRootDirs({
    cwd: process.cwd(),
    settings: rootDir === undefined ? {} : { next: { rootDir } },
  })
    .map((path: string) =>
      relative(fixture, path).replace(/\\/g, "/").replace(/\/$/, ""),
    )
    .sort();

describe("version-scoped Next directory glob replacement", () => {
  it("replaces exactly the reviewed caller without a vulnerable dependency", () => {
    expect(pluginRequire("./package.json").version).toBe("16.3.8");
    expect(pluginRequire("fast-glob/package.json").name).toBe(
      "@smart-merchant/next-root-glob",
    );
    const dist = pluginRequire
      .resolve("./dist/index.js")
      .replace(/index\.js$/, "");
    const importers: string[] = [];
    function visit(dir: string) {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const path = join(dir, entry.name);
        if (entry.isDirectory()) visit(path);
        else if (
          entry.name.endsWith(".js") &&
          readFileSync(path, "utf8").includes('require("fast-glob")')
        )
          importers.push(relative(dist, path));
      }
    }
    visit(dist);
    expect(importers).toEqual(["utils/get-root-dirs.js"]);
    expect(readFileSync(join(dist, importers[0]), "utf8")).toContain(
      "_fastglob.globSync",
    );
    const lock = JSON.parse(
      readFileSync(join(process.cwd(), "package-lock.json"), "utf8"),
    );
    expect(
      Object.keys(lock.packages).filter((key) =>
        /node_modules\/(braces|micromatch)$/.test(key),
      ),
    ).toEqual([]);
  });
  it("preserves default cwd and rejects unsupported adapter calls", () => {
    expect(getRootDirs({ cwd: fixture, settings: {} })).toEqual([fixture]);
    expect(() => adapter.globSync(fixture, { onlyDirectories: false })).toThrow(
      TypeError,
    );
    expect(() =>
      adapter.globSync(fixture, { onlyDirectories: true, cwd: fixture }),
    ).toThrow(TypeError);
    expect(() =>
      adapter.globSync([fixture], { onlyDirectories: true }),
    ).toThrow(TypeError);
  });
  it.each([
    ["literal", join(fixture, "alpha"), ["alpha"]],
    ["wildcard", join(fixture, "*"), ["alpha", "beta"]],
    ["brace", join(fixture, "{alpha,beta}"), ["alpha", "beta"]],
    ["nested", join(fixture, "*/pages"), ["alpha/pages", "beta/pages"]],
    ["missing", join(fixture, "missing"), []],
    ["file", join(fixture, "file.txt"), []],
    [
      "array",
      [join(fixture, "alpha"), 3, join(fixture, "beta")],
      ["alpha", "beta"],
    ],
    ["backslash", join(fixture, "alpha").replace(/\//g, "\\"), ["alpha"]],
    ["relative", relative(process.cwd(), join(fixture, "alpha")), ["alpha"]],
  ])(
    "discovers %s roots without expanding their descendants",
    (_name, pattern, expected) => {
      expect(roots(pattern)).toEqual(expected);
    },
  );
  it("keeps all recommended Next rules enabled and enforces root-dependent rules", async () => {
    const eslint = new ESLint({
      overrideConfig: {
        settings: { next: { rootDir: join(fixture, "alpha") } },
      },
    });
    const config = await eslint.calculateConfigForFile("app/page.tsx");
    for (const name of Object.keys(plugin.configs.recommended.rules)) {
      expect(config.rules[name][0], name).toBeGreaterThan(0);
    }
    const [result] = await eslint.lintText(
      'export default function Page() { return <a href="/about">About</a>; }',
      { filePath: "app/page.tsx" },
    );
    expect(
      result.messages.some(
        (message) =>
          message.ruleId === "@next/next/no-html-link-for-pages" &&
          message.severity === 2,
      ),
    ).toBe(true);
  });
});
