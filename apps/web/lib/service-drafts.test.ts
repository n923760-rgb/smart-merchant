import { describe, expect, it } from "vitest";
import {
  draftLineCents,
  draftTotalCents,
  formatDraftCents,
  validServiceDraftLines,
} from "./service-drafts";

describe("nonfiscal draft money preview", () => {
  it("matches backend HALF_UP for exact fractional cents", () => {
    expect(draftLineCents("1.500", "9.99")).toBe(1499n);
    expect(draftTotalCents([
      { quantity: "1.500", unit_price: "9.99" },
      { quantity: "2.000", unit_price: "10.00" },
    ])).toBe(3499n);
    expect(formatDraftCents(3499n)).toBe("34.99");
  });

  it("avoids IEEE-754 arithmetic for large valid values", () => {
    expect(formatDraftCents(draftLineCents("100.000", "900719925474.09")))
      .toBe("900,719,925,474,090.00");
  });

  it("rejects invalid fractional precision and negative or empty numbers", () => {
    for (const [quantity, price] of [
      ["1.0001", "2.00"],
      ["-2.000", "1.00"],
      ["0.000", "1.00"],
      ["2.000", "-1.00"],
      ["2", "1.005"],
      ["", "1.00"],
    ]) expect(draftLineCents(quantity, price)).toBeNull();
  });

  it("validates service names and size bounds", () => {
    expect(validServiceDraftLines([{
      id: "1", service_name: "Consulting", quantity: "1.000", unit_price: "0.00",
    }])).toBe(true);
    expect(validServiceDraftLines([])).toBe(false);
    expect(validServiceDraftLines([{
      id: "1", service_name: "  ", quantity: "1.000", unit_price: "3.00",
    }])).toBe(false);
  });
});
