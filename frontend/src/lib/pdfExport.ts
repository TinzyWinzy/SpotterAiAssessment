import jsPDF from "jspdf";
import type { DayLog, DutyStatus, RouteInfo, StopMarker } from "./types";

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

  // Summary page
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

  // Day-by-day table
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

  // One page per daily log
  days.forEach((day, idx) => {
    doc.addPage();
    drawLogPage(doc, day, idx, days.length, W, H);
  });

  doc.save(`spotter-trip-plan-${new Date().toISOString().slice(0, 10)}.pdf`);
}

function drawLogPage(
  doc: jsPDF,
  day: DayLog,
  idx: number,
  total: number,
  W: number,
  H: number
) {
  // Title bar
  doc.setFillColor(14, 124, 134);
  doc.rect(0, 0, W, 24, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(11);
  doc.setFont("helvetica", "bold");
  doc.text(`DRIVER'S DAILY LOG — Day ${idx + 1} of ${total} (${day.date})`, 18, 16);
  doc.setTextColor(11, 31, 36);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);

  // Header fields
  doc.text(`Total Miles Today: ${day.total_miles.toFixed(0)}`, 18, 40);
  doc.text(`Date: ${day.date}`, W / 2, 40);
  doc.text(`Carrier: John Doe's Transportation`, 18, 54);
  doc.text(`Office: Washington, D.C.`, W / 2, 54);
  doc.text(`Vehicle: 123, 20544`, 18, 68);
  doc.text(`Co-Driver: —`, W / 2, 68);

  // Grid layout
  const gridLeft = 130;
  const gridTop = 90;
  const gridRight = W - 80;
  const gridW = gridRight - gridLeft;
  const colHourW = gridW / 24;
  const rowH = 30;
  const gridH = rowH * 4;
  const xAxisTop = gridTop + gridH;

  // Grid background
  doc.setDrawColor(31, 41, 55);
  doc.setLineWidth(0.7);
  doc.rect(gridLeft, gridTop, gridW, gridH);

  // Hour ticks
  doc.setLineWidth(0.4);
  for (let h = 0; h <= 24; h++) {
    const x = gridLeft + h * colHourW;
    doc.line(x, gridTop, x, gridTop + gridH);
    if (h < 24) {
      // 15-min subdivs
      [0.25, 0.5, 0.75].forEach((f) => {
        const sx = gridLeft + (h + f) * colHourW;
        doc.setDrawColor(180, 180, 180);
        doc.line(sx, gridTop, sx, gridTop + gridH);
      });
      doc.setDrawColor(31, 41, 55);
      // Hour label
      let label = String(h);
      if (h === 0) label = "Midnight";
      if (h === 12) label = "Noon";
      doc.text(label, x + colHourW / 2, xAxisTop + 11, { align: "center" });
    }
  }

  // Row separators
  for (let r = 1; r < 4; r++) {
    doc.line(gridLeft, gridTop + r * rowH, gridRight, gridTop + r * rowH);
  }

  // Status labels
  doc.setFontSize(9);
  doc.setFont("helvetica", "bold");
  [0, 1, 2, 3].forEach((s) => {
    doc.text(STATUS_LABELS[s as DutyStatus], gridLeft - 4, gridTop + s * rowH + rowH / 2 + 3, {
      align: "right",
    });
  });

  // Status quarter fills
  day.status_quarters.forEach((s, i) => {
    if (s === 0) return;
    const x = gridLeft + i * (colHourW / 4);
    const w = colHourW / 4;
    const [r, g, b] = STATUS_COLORS[s as DutyStatus];
    doc.setFillColor(r, g, b);
    doc.setDrawColor(r, g, b);
    doc.rect(x, gridTop + s * rowH + 1, w, rowH - 2, "F");
  });

  // Total Hours column
  const totalColLeft = gridRight;
  const totalColW = 70;
  doc.setDrawColor(31, 41, 55);
  doc.setFillColor(255, 255, 255);
  doc.rect(totalColLeft, gridTop, totalColW, gridH);
  doc.setFontSize(8);
  doc.text("Total Hours", totalColLeft + totalColW / 2, gridTop - 4, { align: "center" });
  const rows = [
    { label: "Off", val: day.totals.off_duty },
    { label: "Sleeper", val: day.totals.sleeper },
    { label: "Driving", val: day.totals.driving },
    { label: "On Duty", val: day.totals.on_duty },
  ];
  rows.forEach((row, i) => {
    doc.setFont("helvetica", "normal");
    doc.text(row.label, totalColLeft + 5, gridTop + i * rowH + 13);
    doc.setFont("helvetica", "bold");
    doc.text(row.val.toFixed(2), totalColLeft + totalColW - 5, gridTop + i * rowH + 13, {
      align: "right",
    });
  });

  // Remarks
  const remarksTop = xAxisTop + 30;
  const remarksH = 100;
  doc.setDrawColor(31, 41, 55);
  doc.rect(gridLeft, remarksTop, W - gridLeft - 18, remarksH);
  doc.setFontSize(9);
  doc.setFont("helvetica", "bold");
  doc.text("REMARKS", gridLeft + 6, remarksTop + 12);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(8);
  const remarks = day.events
    .filter((e) => e.remark && e.remark !== "Driving" && !e.remark.includes("home terminal"))
    .slice(0, 8);
  remarks.forEach((e, i) => {
    const time = new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });
    doc.text(`${time} — ${e.location.label} — ${e.remark}`, gridLeft + 6, remarksTop + 26 + i * 9);
  });
}
