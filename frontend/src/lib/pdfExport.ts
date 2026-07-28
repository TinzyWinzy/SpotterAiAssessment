import jsPDF from "jspdf";
import type { Trip } from "./types";

const BRAND = "#0e7c86";
const DARK = "#0b1f24";
const GRAY = "#6b7280";
const LIGHT_GRAY = "#e5e7eb";
const LIGHT_BG = "#f0fdf9";

export function exportTripSheet(trip: Trip): void {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const W = doc.internal.pageSize.getWidth();
  const M = 15;

  let y = 15;

  doc.setFillColor(BRAND);
  doc.rect(0, 0, W, 22, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(14);
  doc.text("TruckLedger", M, 10);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.text("Trip Sheet", M, 16);

  doc.setFontSize(8);
  doc.text(`#TRIP-${trip.id}`, W - M, 10, { align: "right" });
  doc.text(new Date(trip.created_at).toLocaleDateString(), W - M, 16, { align: "right" });

  doc.setTextColor(DARK);
  y = 30;

  // Vehicle & Driver section
  doc.setFillColor(LIGHT_BG);
  doc.rect(M, y, W - 2 * M, 18, "F");
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("Vehicle", M + 3, y + 5);
  doc.text("Driver", W / 2 + 3, y + 5);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(trip.vehicle_plate || "N/A", M + 3, y + 11);
  doc.text(trip.driver_name || "N/A", W / 2 + 3, y + 11);
  doc.setFontSize(7);
  doc.setTextColor(GRAY);
  doc.text(`Status: ${trip.status.replace(/_/g, " ")}`, M + 40, y + 11);
  y += 22;

  // Route section
  doc.setTextColor(DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("Route", M, y);
  y += 5;

  doc.setDrawColor(LIGHT_GRAY);
  doc.setLineWidth(0.3);
  doc.line(M, y, W - M, y);
  y += 4;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text(`Origin: ${trip.origin}`, M, y);
  y += 5;
  if (trip.waypoints.length > 0) {
    trip.waypoints.forEach((wp: string) => {
      doc.text(`Via: ${wp}`, M + 10, y);
      y += 5;
    });
  }
  doc.text(`Destination: ${trip.destination}`, M, y);
  y += 5;
  doc.setFontSize(7);
  doc.setTextColor(GRAY);
  doc.text(`Distance: ${trip.distance_km} km  |  Load: ${trip.load_type}`, M, y);
  y += 10;

  // Cost breakdown table
  doc.setTextColor(DARK);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(9);
  doc.text("Cost Breakdown (USD)", M, y);
  y += 5;

  const colW = (W - 2 * M) / 3;

  doc.setFillColor(DARK);
  doc.rect(M, y, W - 2 * M, 5, "F");
  doc.setTextColor(255, 255, 255);
  doc.setFontSize(7);
  doc.text("Item", M + 2, y + 3.5);
  doc.text("Estimated", M + colW + 2, y + 3.5);
  doc.text("Actual", M + 2 * colW + 2, y + 3.5);
  doc.setTextColor(DARK);
  y += 6;

  const rows: { label: string; est: number | null; act: number | null }[] = [
    { label: "Fuel", est: trip.estimated_fuel_cost_usd, act: trip.actual_fuel_cost_usd },
    { label: "Driver Pay", est: trip.estimated_driver_pay_usd, act: trip.actual_driver_pay_usd },
    { label: "Border Fees", est: trip.estimated_border_fees_usd || null, act: trip.actual_border_fees_usd || null },
    { label: "Tolls", est: trip.estimated_tolls_usd || null, act: null },
    { label: "Total Cost", est: trip.estimated_total_cost_usd, act: trip.actual_total_cost_usd },
    { label: "Revenue", est: null, act: trip.revenue_usd },
  ];

  rows.forEach((row, i) => {
    if (row.est === 0 && !row.act) return;
    const isBold = row.label === "Total Cost" || row.label === "Revenue";
    if (i % 2 === 0 && !isBold) {
      doc.setFillColor(LIGHT_BG);
      doc.rect(M, y - 1, W - 2 * M, 5, "F");
    }
    doc.setFont("helvetica", isBold ? "bold" : "normal");
    doc.setFontSize(7);
    doc.text(row.label, M + 2, y + 2);
    doc.text(row.est != null ? `$${row.est.toFixed(2)}` : "-", M + colW + 2, y + 2);
    doc.text(row.act != null ? `$${row.act.toFixed(2)}` : "-", M + 2 * colW + 2, y + 2);
    y += 5;
  });

  // Profit/Loss line
  const revenue = trip.revenue_usd ?? 0;
  const cost = trip.actual_total_cost_usd ?? trip.estimated_total_cost_usd;
  const profit = revenue - cost;
  if (revenue > 0 || trip.actual_total_cost_usd) {
    y += 2;
    doc.setFillColor(profit >= 0 ? "#ecfdf5" : "#fef2f2");
    doc.rect(M, y - 1, W - 2 * M, 5, "F");
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text(profit >= 0 ? "PROFIT" : "LOSS", M + 2, y + 2.5);
    doc.text(`$${Math.abs(profit).toFixed(2)}`, M + colW + 2, y + 2.5);
    doc.setFontSize(7);
    doc.setFont("helvetica", "normal");
    doc.text(profit >= 0 ? "Trip was profitable" : "Trip ran at a loss", M + 2 * colW + 2, y + 2.5);
    y += 8;
  }

  // Signature section
  y = Math.max(y + 8, 210);
  doc.setDrawColor(LIGHT_GRAY);
  doc.setLineWidth(0.3);
  doc.line(M, y, W - M, y);
  y += 6;

  doc.setFont("helvetica", "bold");
  doc.setFontSize(8);
  doc.text("Signatures", M, y);
  y += 8;

  doc.setFont("helvetica", "normal");
  doc.setFontSize(7);
  doc.text("Driver:", M, y);
  doc.line(M + 15, y + 3, M + 55, y + 3);
  doc.text("Date:", M + 58, y);
  doc.line(M + 65, y + 3, M + 95, y + 3);

  doc.text("Customer:", M + 100, y);
  doc.line(M + 115, y + 3, M + 155, y + 3);
  doc.text("Date:", M + 158, y);
  doc.line(M + 165, y + 3, W - M, y + 3);

  y += 10;
  doc.setTextColor(GRAY);
  doc.setFontSize(6);
  doc.text(`Generated by TruckLedger on ${new Date().toLocaleString()}`, M, y);

  doc.save(`truckledger-trip-${trip.id}-${new Date().toISOString().slice(0, 10)}.pdf`);
}
