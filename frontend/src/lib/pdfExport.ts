import jsPDF from "jspdf";
import type { DayLog, DayLogRecap, DutyStatus, RouteInfo, StopMarker } from "./types";

const STATUS_COLORS: Record<DutyStatus, [number, number, number]> = {
  0: [255, 255, 255],
  1: [125, 211, 192],
  2: [14, 124, 134],
  3: [253, 230, 138],
};

const STATUS_LABELS: Record<DutyStatus, string> = {
  0: "1. Off Duty",
  1: "2. Sleeper Berth",
  2: "3. Driving",
  3: "4. On Duty (Not Driving)",
};

export function exportTripPdf(
  days: DayLog[],
  route: RouteInfo,
  stops: StopMarker[]
): void {
  const doc = new jsPDF({ orientation: "landscape", unit: "pt", format: "letter" });
  const W = doc.internal.pageSize.getWidth();
  const H = doc.internal.pageSize.getHeight();

  doc.setFillColor(14, 124, 134);
  doc.rect(0, 0, W, 50, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(18);
  doc.setFont("helvetica", "bold");
  doc.text("SPOTTER — HOS Trip Plan Summary", 24, 32);
  doc.setTextColor(11, 31, 36);
  doc.setFontSize(11);
  doc.setFont("helvetica", "normal");

  let y = 80;
  doc.text(`Total Distance: ${route.distance_mi.toFixed(0)} mi`, 24, y);
  y += 16;
  doc.text(`Estimated Drive Time: ${route.duration_h.toFixed(1)} hr`, 24, y);
  y += 16;
  doc.text(`Number of Days: ${days.length}`, 24, y);
  y += 16;
  doc.text(`Stops: ${stops.map((s) => `${s.kind}=${s.label}`).join("  →  ")}`, 24, y);
  y += 28;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(12);
  doc.text("Day-by-Day Breakdown", 24, y);
  y += 18;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(10);

  days.forEach((day, idx) => {
    if (y > H - 60) {
      doc.addPage();
      y = 40;
    }
    doc.setFont("helvetica", "bold");
    doc.text(`Day ${idx + 1} — ${day.date}`, 24, y);
    doc.setFont("helvetica", "normal");
    y += 14;
    doc.text(
      `  Off: ${day.totals.off_duty.toFixed(2)}h  Sleeper: ${day.totals.sleeper.toFixed(2)}h  Driving: ${day.totals.driving.toFixed(2)}h  On Duty: ${day.totals.on_duty.toFixed(2)}h  (${day.total_miles.toFixed(0)} mi)`,
      24,
      y
    );
    y += 16;
  });

  days.forEach((day, idx) => {
    doc.addPage();
    drawLogPage(doc, day, idx, days.length, W);
  });

  doc.save(`spotter-trip-plan-${new Date().toISOString().slice(0, 10)}.pdf`);
}

function fmt(n: number | undefined): string {
  return n === undefined ? "—" : n.toFixed(2);
}

function drawLogPage(
  doc: jsPDF,
  day: DayLog,
  idx: number,
  total: number,
  W: number
) {
  const recap: DayLogRecap = day.recap || {
    cycle_used_hrs: 0,
    on_duty_today: 0,
    last_8day_total: 0,
    last_7day_total: 0,
    tomorrow_70_budget: 0,
    last_5day_total: 0,
    last_7day_total_60: 0,
    tomorrow_60_budget: 0,
    took_34h_restart: false,
    approximate: false,
  };

  doc.setFillColor(14, 124, 134);
  doc.rect(0, 0, W, 20, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(10);
  doc.setFont("helvetica", "bold");
  doc.text(`DRIVERS DAILY LOG — Day ${idx + 1} of ${total} (${day.date})`, 18, 14);
  doc.setTextColor(11, 31, 36);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);

  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text("Drivers Daily Log", 18, 32);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text(`Date: ${day.date.replace(/-/g, " / ")}    (24 hours)`, 18, 46);
  const fromTime = day.events.length > 0
    ? new Date(day.events[0].start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
    : "00:00";
  const lastEv = day.events[day.events.length - 1];
  const toTime = lastEv
    ? new Date(new Date(lastEv.start).getTime() + lastEv.duration_h * 3600 * 1000)
        .toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
    : "24:00";
  doc.text(`From: ${fromTime}    To: ${toTime}`, 18, 58);
  doc.text(`Total Miles Driving Today: ${day.total_miles.toFixed(0)}`, 18, 70);
  doc.text(`Total Mileage Today: ${day.total_miles.toFixed(0)}`, W / 2, 70);
  doc.text(`Name of Carrier: John Doe's Transportation`, 18, 82);
  doc.text(`Main Office Address: Washington, D.C.`, W / 2, 82);

  doc.setFont("helvetica", "bold");
  doc.text("Original — File at home terminal.", W - 18, 32, { align: "right" });
  doc.setFont("helvetica", "italic");
  doc.text("Duplicates — retain for 8 days.", W - 18, 42, { align: "right" });
  doc.setFont("helvetica", "normal");
  doc.text(`Truck/Trailer #: 123, 20544`, W - 18, 54, { align: "right" });
  doc.text(`Home Terminal: Washington, D.C.`, W - 18, 64, { align: "right" });
  doc.text(`Co-Driver: —`, W - 18, 74, { align: "right" });

  const gridLeft = 130;
  const gridTop = 100;
  const gridRight = W - 80;
  const gridW = gridRight - gridLeft;
  const colHourW = gridW / 24;
  const rowH = 26;
  const gridH = rowH * 4;
  const xAxisTop = gridTop + gridH;

  doc.setDrawColor(31, 41, 55);
  doc.setLineWidth(0.7);
  doc.rect(gridLeft, gridTop, gridW, gridH);

  doc.setLineWidth(0.4);
  for (let h = 0; h <= 24; h++) {
    const x = gridLeft + h * colHourW;
    doc.line(x, gridTop, x, gridTop + gridH);
    if (h < 24) {
      [0.25, 0.5, 0.75].forEach((f) => {
        const sx = gridLeft + (h + f) * colHourW;
        doc.setDrawColor(180, 180, 180);
        doc.line(sx, gridTop, sx, gridTop + gridH);
      });
      doc.setDrawColor(31, 41, 55);
      let label = String(h);
      if (h === 0) label = "Mid-night";
      if (h === 12) label = "Noon";
      doc.setFontSize(7);
      doc.text(label, x + colHourW / 2, xAxisTop + 9, { align: "center" });
    }
  }

  for (let r = 1; r < 4; r++) {
    doc.line(gridLeft, gridTop + r * rowH, gridRight, gridTop + r * rowH);
  }

  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  [0, 1, 2, 3].forEach((s) => {
    doc.text(STATUS_LABELS[s as DutyStatus], gridLeft - 4, gridTop + s * rowH + rowH / 2 + 3, {
      align: "right",
    });
  });

  day.status_quarters.forEach((s, i) => {
    if (s === 0) return;
    const x = gridLeft + i * (colHourW / 4);
    const w = colHourW / 4;
    const [r, g, b] = STATUS_COLORS[s as DutyStatus];
    doc.setFillColor(r, g, b);
    doc.setDrawColor(r, g, b);
    doc.rect(x, gridTop + s * rowH + 1, w, rowH - 2, "F");
  });

  const totalColLeft = gridRight;
  const totalColW = 70;
  doc.setDrawColor(31, 41, 55);
  doc.setFillColor(255, 255, 255);
  doc.rect(totalColLeft, gridTop, totalColW, gridH);
  doc.setFontSize(7);
  doc.text("Total Hours", totalColLeft + totalColW / 2, gridTop - 3, { align: "center" });
  const rows = [
    { label: "Off", val: day.totals.off_duty },
    { label: "Sleeper", val: day.totals.sleeper },
    { label: "Driving", val: day.totals.driving },
    { label: "On Duty", val: day.totals.on_duty },
  ];
  rows.forEach((row, i) => {
    doc.setFont("helvetica", "normal");
    doc.setFontSize(7);
    doc.text(row.label, totalColLeft + 5, gridTop + i * rowH + 11);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text(row.val.toFixed(2), totalColLeft + totalColW - 5, gridTop + i * rowH + 11, {
      align: "right",
    });
  });

  const remarksTop = xAxisTop + 16;
  const remarksH = 90;
  const remarksMainW = (W - 36 - gridLeft) * 0.62;
  const shippingLeft = gridLeft + remarksMainW + 10;
  const shippingW = W - 18 - shippingLeft;

  doc.setDrawColor(31, 41, 55);
  doc.rect(gridLeft, remarksTop, remarksMainW, remarksH);
  doc.setFontSize(9);
  doc.setFont("helvetica", "bold");
  doc.text("REMARKS", gridLeft + 6, remarksTop + 10);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  const remarks = day.events
    .filter((e) => e.remark && e.remark !== "Driving" && !e.remark.includes("home terminal"))
    .slice(0, 7);
  remarks.forEach((e, i) => {
    const time = new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    const line = `${time} — ${e.location.label} — ${e.remark}`;
    const truncated = line.length > 70 ? line.slice(0, 67) + "..." : line;
    doc.text(truncated, gridLeft + 6, remarksTop + 22 + i * 9);
  });

  doc.rect(shippingLeft, remarksTop, shippingW, remarksH);
  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  doc.text("Shipping Documents", shippingLeft + 6, remarksTop + 10);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(6);
  doc.text("DVL or Manifest No. or", shippingLeft + 6, remarksTop + 24);
  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  doc.text("101601", shippingLeft + 6, remarksTop + 44);
  doc.setDrawColor(180, 180, 180);
  doc.setLineWidth(0.3);
  doc.line(shippingLeft + 6, remarksTop + 52, shippingLeft + shippingW - 6, remarksTop + 52);
  doc.setFontSize(8);
  doc.text("Shipper & Commodity", shippingLeft + 6, remarksTop + 68);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  const pickupLoc = day.events.find((e) => e.remark === "Pickup")?.location.label || "—";
  doc.text(pickupLoc, shippingLeft + 6, remarksTop + 80);

  const italicTop = remarksTop + remarksH + 4;
  doc.setFont("helvetica", "italic");
  doc.setFontSize(7);
  doc.setTextColor(71, 85, 105);
  doc.text(
    "Enter name of place you reported and where released from work and when and where each change of duty occurred.",
    gridLeft, italicTop + 6,
  );
  doc.text("Use time standard of home terminal.", gridLeft, italicTop + 16);
  doc.setTextColor(11, 31, 36);

  const recapTop = italicTop + 30;
  const recapH = 160;
  doc.setFillColor(14, 124, 134);
  doc.rect(18, recapTop, W - 36, 16, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.text("Recap (completed at end of day)", 24, recapTop + 11);
  doc.text("70 Hour / 8 Day Drivers", 18 + (W - 36) / 3 + 6, recapTop + 11);
  doc.text("60 Hour / 7 Day Drivers", 18 + 2 * (W - 36) / 3 + 6, recapTop + 11);
  doc.setTextColor(11, 31, 36);

  const bodyTop = recapTop + 16;
  const bodyH = recapH - 16;
  const cellW = (W - 36) / 3;
  doc.setDrawColor(31, 41, 55);
  doc.setLineWidth(0.7);
  [cellW, cellW * 2].forEach((dx) => {
    const x = 18 + dx;
    doc.line(x, bodyTop, x, bodyTop + bodyH);
  });
  doc.rect(18, bodyTop, W - 36, bodyH);

  doc.setFontSize(8);
  doc.setFont("helvetica", "bold");
  doc.text("On duty hours", 24, bodyTop + 12);
  doc.setFont("helvetica", "italic");
  doc.setFontSize(7);
  doc.setTextColor(71, 85, 105);
  doc.text("(Total lines 3 & 4)", 24, bodyTop + 22);
  doc.setTextColor(11, 31, 36);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  doc.text("Today:", 24, bodyTop + 40);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(day.totals.driving + day.totals.on_duty), cellW - 6, bodyTop + 40, { align: "right" });
  if (recap.approximate) {
    doc.setFont("helvetica", "italic");
    doc.setFontSize(6);
    doc.setTextColor(71, 85, 105);
    doc.text("Approx. — see note", 24, bodyTop + 60);
    doc.setTextColor(11, 31, 36);
  }

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("A.", cellW + 24, bodyTop + 12);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours on duty last 7 days including today", cellW + 36, bodyTop + 12);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.last_7day_total), 18 + 2 * cellW - 6, bodyTop + 12, { align: "right" });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("B.", cellW + 24, bodyTop + 32);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours available tomorrow (70 hr minus A)", cellW + 36, bodyTop + 32);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.tomorrow_70_budget), 18 + 2 * cellW - 6, bodyTop + 32, { align: "right" });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("F.", cellW + 24, bodyTop + 60);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours on duty last 8 days including today", cellW + 36, bodyTop + 60);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.last_8day_total), 18 + 2 * cellW - 6, bodyTop + 60, { align: "right" });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("C.", 2 * cellW + 24, bodyTop + 12);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours on duty last 5 days including today", 2 * cellW + 36, bodyTop + 12);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.last_5day_total), W - 24, bodyTop + 12, { align: "right" });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("D.", 2 * cellW + 24, bodyTop + 32);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours on duty last 7 days including today", 2 * cellW + 36, bodyTop + 32);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.last_7day_total_60), W - 24, bodyTop + 32, { align: "right" });

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("E.", 2 * cellW + 24, bodyTop + 60);
  doc.setFont("helvetica", "normal");
  doc.text("Total hours available tomorrow (60 hr minus C)", 2 * cellW + 36, bodyTop + 60);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(10);
  doc.text(fmt(recap.tomorrow_60_budget), W - 24, bodyTop + 60, { align: "right" });

  if (recap.took_34h_restart) {
    doc.setFillColor(254, 243, 199);
    doc.setDrawColor(146, 64, 14);
    doc.roundedRect(W - 140, bodyTop + 80, 120, 40, 2, 2, "FD");
    doc.setTextColor(146, 64, 14);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text("34-hr restart", W - 134, bodyTop + 94);
    doc.setFontSize(6);
    doc.text("taken on this day", W - 134, bodyTop + 104);
    doc.text("→ 60/70 hrs available", W - 134, bodyTop + 114);
    doc.setTextColor(11, 31, 36);
  }

  doc.setFont("helvetica", "italic");
  doc.setFontSize(6);
  doc.setTextColor(71, 85, 105);
  doc.text(
    "* If you took 34 consecutive hours off duty you have 60/70 hours available",
    W - 24, recapTop + recapH - 2, { align: "right" },
  );
  doc.setTextColor(11, 31, 36);

  const footerY = recapTop + recapH + 8;
  doc.setDrawColor(180, 180, 180);
  doc.setLineWidth(0.3);
  doc.line(18, footerY, W - 18, footerY);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(6);
  doc.setTextColor(71, 85, 105);
  doc.text("I certify that these entries are true and correct — Tinotenda Duma", 18, footerY + 8);
  doc.text(`Shipping Doc: 101601`, W - 24, footerY + 8, { align: "right" });
  doc.setTextColor(11, 31, 36);
}
