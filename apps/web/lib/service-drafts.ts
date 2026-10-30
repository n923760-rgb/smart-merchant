/** UI-only arithmetic preview; backend Decimal remains authoritative. */
const QTY = /^\d{1,9}(?:\.\d{1,3})?$/;
const PRICE = /^\d{1,12}(?:\.\d{1,2})?$/;

export type DraftInputLine = {
  id: string;
  service_name: string;
  quantity: string;
  unit_price: string;
};

export type ServiceDraft = {
  id: string;
  request_id: string;
  status: "DRAFT";
  document_kind: "INTERNAL_SERVICE_DRAFT";
  tax_status: "NOT_EVALUATED";
  currency: "SAR";
  customer_name: string;
  customer_email: string | null;
  amount_before_tax: string;
  lines: {
    service_name: string;
    line_number: number;
    quantity: string;
    unit_price: string;
    line_total: string;
  }[];
};

function scaled(value: string, decimals: number): bigint | null {
  if (typeof value !== "string" || !(decimals === 3 ? QTY : PRICE).test(value))
    return null;
  const [whole, fraction = ""] = value.split(".");
  return BigInt(whole) * 10n ** BigInt(decimals)
    + BigInt((fraction.padEnd(decimals, "0")) || "0");
}

export function draftLineCents(
  quantity: string,
  unitPrice: string,
): bigint | null {
  const mills = scaled(quantity, 3);
  const cents = scaled(unitPrice, 2);
  if (mills === null || cents === null || mills <= 0n) return null;
  // HALF_UP for nonnegative SAR amounts: multiply exact integer units,
  // then round the fractional cent up at half.
  return (mills * cents + 500n) / 1000n;
}

export function draftTotalCents(
  lines: readonly Pick<DraftInputLine, "quantity" | "unit_price">[],
): bigint | null {
  if (lines.length === 0 || lines.length > 100) return null;
  let total = 0n;
  for (const line of lines) {
    const cents = draftLineCents(line.quantity, line.unit_price);
    if (cents === null) return null;
    total += cents;
  }
  return total;
}

export function formatDraftCents(value: bigint | null): string {
  if (value === null || value < 0n) return "—";
  const integer = value / 100n;
  const decimal = (value % 100n).toString().padStart(2, "0");
  return `${integer.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",")}.${decimal}`;
}

export function validServiceDraftLines(lines: DraftInputLine[]): boolean {
  return lines.length > 0 && lines.length <= 100 &&
    lines.every((line) => line.service_name.trim().length > 0 &&
      line.service_name.trim().length <= 180 &&
      draftLineCents(line.quantity, line.unit_price) !== null);
}
