/**
 * Built-in MeasurementUnit definitions — Phase 2 wiring.
 *
 * Locks in the conversion math for mm, in, pt, pica, agate so a
 * future refactor of MeasureTool's readout can't silently break the
 * unit values consumers see in the popover.
 *
 * Conversions are anchored to the inch (exact: 25.4 mm = 1 in =
 * 72 pt = 6 picas = 13.0909... agate). PDF coordinate space is
 * always in points; everything else is derived.
 */

import { describe, expect, it } from "vitest";

import {
  agateUnit,
  allMeasurementUnits,
  defaultMeasurementUnits,
  inchUnit,
  mmUnit,
  picaUnit,
  pointUnit,
} from "../../src/core/units";

const ONE_INCH_PTS = 72;

describe("mmUnit", () => {
  it("1 inch = 25.4 mm", () => {
    expect(mmUnit.fromPoints(ONE_INCH_PTS)).toBeCloseTo(25.4, 6);
  });

  it("inverse round-trips", () => {
    expect(mmUnit.toPoints(25.4)).toBeCloseTo(ONE_INCH_PTS, 6);
  });

  it("0 pts = 0 mm", () => {
    expect(mmUnit.fromPoints(0)).toBe(0);
  });
});

describe("inchUnit", () => {
  it("72 pts = 1 in", () => {
    expect(inchUnit.fromPoints(ONE_INCH_PTS)).toBeCloseTo(1, 6);
  });

  it("inverse round-trips", () => {
    expect(inchUnit.toPoints(1)).toBe(ONE_INCH_PTS);
  });
});

describe("pointUnit (identity)", () => {
  it("fromPoints is identity", () => {
    expect(pointUnit.fromPoints(123.45)).toBe(123.45);
  });

  it("toPoints is identity", () => {
    expect(pointUnit.toPoints(67.89)).toBe(67.89);
  });
});

describe("picaUnit", () => {
  it("12 pts = 1 pica", () => {
    expect(picaUnit.fromPoints(12)).toBe(1);
  });

  it("72 pts = 6 picas", () => {
    expect(picaUnit.fromPoints(72)).toBe(6);
  });

  it("inverse round-trips", () => {
    expect(picaUnit.toPoints(6)).toBe(72);
  });
});

describe("agateUnit", () => {
  it("5.5 pts = 1 agate", () => {
    expect(agateUnit.fromPoints(5.5)).toBeCloseTo(1, 6);
  });

  it("72 pts ≈ 13.09 agate (1 inch)", () => {
    expect(agateUnit.fromPoints(72)).toBeCloseTo(13.0909, 4);
  });

  it("inverse round-trips", () => {
    expect(agateUnit.toPoints(2)).toBe(11);
  });
});

describe("manifest exports", () => {
  it("allMeasurementUnits ordering: mm, in, pt, pica, agate", () => {
    expect(allMeasurementUnits.map((u) => u.id)).toEqual([
      "mm",
      "in",
      "pt",
      "pica",
      "agate",
    ]);
  });

  it("defaultMeasurementUnits is the 3-unit subset", () => {
    expect(defaultMeasurementUnits.map((u) => u.id)).toEqual([
      "mm",
      "in",
      "pt",
    ]);
  });

  it("each unit has stable id + label", () => {
    expect(mmUnit).toMatchObject({ id: "mm", label: "mm" });
    expect(inchUnit).toMatchObject({ id: "in", label: "in" });
    expect(pointUnit).toMatchObject({ id: "pt", label: "pt" });
    expect(picaUnit).toMatchObject({ id: "pica", label: "pc" });
    expect(agateUnit).toMatchObject({ id: "agate", label: "ag" });
  });
});
