/**
 * Plugin registry — Phase 2 `replaces` override mechanism.
 *
 * Locks in the contract from Q2-D mitigation #1: a third-party
 * plugin can opt-in replace a LintPDF first-party plugin by
 * declaring `replaces: "lintpdf.X"` on its manifest. The registry
 * filters the original out of slot lookups; both plugins remain in
 * `listAll()` for inspection.
 */

import { afterEach, describe, expect, it } from "vitest";

import {
  _resetRegistryForTesting,
  getPluginsForSlot,
  listAll,
  register,
  unregister,
} from "../../src/core/plugin/registry";
import type { PanelPlugin } from "../../src/core/plugin/types";

const mkPanel = (overrides: Partial<PanelPlugin> = {}): PanelPlugin => ({
  id: "test.panel.default",
  version: "1.0.0",
  slot: "panel.right",
  title: "Default",
  mount: () => null,
  ...overrides,
});

describe("plugin registry — basic registration", () => {
  afterEach(() => _resetRegistryForTesting());

  it("registers and returns a plugin in its slot", () => {
    register(mkPanel());
    const matches = getPluginsForSlot("panel.right");
    expect(matches).toHaveLength(1);
    expect(matches[0]?.id).toBe("test.panel.default");
  });

  it("throws on duplicate id", () => {
    register(mkPanel());
    expect(() => register(mkPanel())).toThrow(
      /already registered: test.panel.default/,
    );
  });

  it("unregister removes a plugin from slot lookups", () => {
    register(mkPanel());
    unregister("test.panel.default");
    expect(getPluginsForSlot("panel.right")).toHaveLength(0);
  });

  it("orders by `order` asc when present", () => {
    register(mkPanel({ id: "a", order: 30 }));
    register(mkPanel({ id: "b", order: 10 }));
    register(mkPanel({ id: "c", order: 20 }));
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["b", "c", "a"]);
  });
});

describe("plugin registry — `replaces` override", () => {
  afterEach(() => _resetRegistryForTesting());

  it("filters the replaced plugin out of slot lookups", () => {
    register(mkPanel({ id: "lintpdf.findings", title: "LintPDF" }));
    register(
      mkPanel({
        id: "vendor.findings",
        title: "Vendor",
        replaces: "lintpdf.findings",
      }),
    );
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["vendor.findings"]);
  });

  it("works regardless of registration order — overrider first", () => {
    register(
      mkPanel({
        id: "vendor.findings",
        replaces: "lintpdf.findings",
      }),
    );
    register(mkPanel({ id: "lintpdf.findings" }));
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["vendor.findings"]);
  });

  it("works regardless of registration order — target first", () => {
    register(mkPanel({ id: "lintpdf.findings" }));
    register(
      mkPanel({
        id: "vendor.findings",
        replaces: "lintpdf.findings",
      }),
    );
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["vendor.findings"]);
  });

  it("listAll includes the overridden plugin (filtering only happens at slot lookup)", () => {
    register(mkPanel({ id: "lintpdf.findings" }));
    register(
      mkPanel({
        id: "vendor.findings",
        replaces: "lintpdf.findings",
      }),
    );
    const ids = listAll()
      .map((p) => p.id)
      .sort();
    expect(ids).toEqual(["lintpdf.findings", "vendor.findings"]);
  });

  it("throws when two plugins claim the same `replaces` target", () => {
    register(
      mkPanel({
        id: "vendor1.findings",
        replaces: "lintpdf.findings",
      }),
    );
    expect(() =>
      register(
        mkPanel({
          id: "vendor2.findings",
          replaces: "lintpdf.findings",
        }),
      ),
    ).toThrow(
      /override conflict: 'vendor2.findings' tried to replace 'lintpdf.findings', but 'vendor1.findings' already does/,
    );
  });

  it("unregister releases the override slot for a subsequent claim", () => {
    register(mkPanel({ id: "lintpdf.findings" }));
    register(
      mkPanel({
        id: "vendor1.findings",
        replaces: "lintpdf.findings",
      }),
    );
    unregister("vendor1.findings");
    // Now vendor2 can claim the same override.
    register(
      mkPanel({
        id: "vendor2.findings",
        replaces: "lintpdf.findings",
      }),
    );
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["vendor2.findings"]);
  });

  it("when overrider is unregistered, the original re-emerges in slot lookups", () => {
    register(mkPanel({ id: "lintpdf.findings", title: "Original" }));
    register(
      mkPanel({
        id: "vendor.findings",
        title: "Vendor",
        replaces: "lintpdf.findings",
      }),
    );
    expect(getPluginsForSlot("panel.right").map((p) => p.id)).toEqual([
      "vendor.findings",
    ]);
    unregister("vendor.findings");
    expect(getPluginsForSlot("panel.right").map((p) => p.id)).toEqual([
      "lintpdf.findings",
    ]);
  });

  it("replacing a non-yet-registered target doesn't fail; takes effect when target appears", () => {
    register(
      mkPanel({
        id: "vendor.findings",
        replaces: "lintpdf.findings",
      }),
    );
    expect(getPluginsForSlot("panel.right").map((p) => p.id)).toEqual([
      "vendor.findings",
    ]);
    // Target appears later; gets shadowed immediately.
    register(mkPanel({ id: "lintpdf.findings" }));
    expect(getPluginsForSlot("panel.right").map((p) => p.id)).toEqual([
      "vendor.findings",
    ]);
  });

  it("cross-slot override still removes the target from its slot", () => {
    // Vendor decides to replace the panel with a toolbar widget — odd
    // but valid. The original panel disappears from panel.right; the
    // vendor's toolbar shows up in toolbar.top.
    register(mkPanel({ id: "lintpdf.findings", slot: "panel.right" }));
    register({
      id: "vendor.findings",
      version: "1.0.0",
      slot: "toolbar.top",
      replaces: "lintpdf.findings",
      mount: () => null,
    });
    expect(getPluginsForSlot("panel.right").map((p) => p.id)).toEqual([]);
    expect(getPluginsForSlot("toolbar.top").map((p) => p.id)).toEqual([
      "vendor.findings",
    ]);
  });

  it("override does not break ordering for sibling plugins in the slot", () => {
    register(mkPanel({ id: "lintpdf.findings", order: 20 }));
    register(mkPanel({ id: "lintpdf.history", order: 30 }));
    register(
      mkPanel({
        id: "vendor.findings",
        order: 25,
        replaces: "lintpdf.findings",
      }),
    );
    const ids = getPluginsForSlot("panel.right").map((p) => p.id);
    expect(ids).toEqual(["vendor.findings", "lintpdf.history"]);
  });
});
