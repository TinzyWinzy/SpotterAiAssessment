import type { DayLog, DayLogRecap, DutyStatus } from "../lib/types";

const STATUS_COLORS: Record<DutyStatus, string> = {
  0: "#ffffff",   // Off Duty — white/empty
  1: "#7dd3c0",   // Sleeper Berth — teal-green
  2: "#0e7c86",   // Driving — spotter teal
  3: "#fde68a",   // On Duty (Not Driving) — light yellow
};

const STATUS_LABELS: Record<DutyStatus, string> = {
  0: "1. Off Duty",
  1: "2. Sleeper Berth",
  2: "3. Driving",
  3: "4. On Duty (Not Driving)",
};

interface Props {
  day: DayLog;
  carrierName?: string;
  mainOffice?: string;
  truckNumber?: string;
  shippingDoc?: string;
  coDriver?: string;
  driverName?: string;
  homeTerminal?: string;
  index: number;
  totalDays?: number;
}

export function DailyLog({
  day,
  carrierName = "John Doe's Transportation",
  mainOffice = "Washington, D.C.",
  truckNumber = "123, 20544",
  shippingDoc = "101601",
  coDriver = "",
  driverName = "Tinotenda Duma",
  homeTerminal = "Washington, D.C.",
  index,
}: Props) {
  const W = 900;
  const H = 940;

  // Layout
  const headerH = 115;
  const gridTop = headerH;
  const gridLeft = 130;
  const gridRight = W - 80;
  const gridW = gridRight - gridLeft;
  const colHourW = gridW / 24;
  const rowH = 32;
  const gridH = rowH * 4;
  const xAxisTop = gridTop + gridH;
  const xAxisH = 20;
  const totalColLeft = gridRight;
  const totalColW = 70;

  // Remarks (left 2/3) + Shipping (right 1/3) split
  const remarksTop = xAxisTop + xAxisH + 12;
  const remarksH = 130;
  const remarksLeft = gridLeft;
  const remarksMainW = (W - 20 - gridLeft) * 0.62;
  const shippingLeft = remarksLeft + remarksMainW + 10;
  const shippingW = W - 20 - shippingLeft;
  const italicTop = remarksTop + remarksH + 4;
  const italicH = 28;

  // Recap table
  const recapTop = italicTop + italicH + 14;
  const recapH = 240;
  const sidebarCol = 130;             // right sidebar "If you took 34..."

  const totalMiles = day.total_miles;
  const totalMileage = day.total_miles;  // could include deadhead later

  // Day start/end from events
  const fromTime = day.events.length > 0
    ? new Date(day.events[0].start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
    : "00:00";
  const toTime = day.events.length > 0
    ? new Date(
        new Date(day.events[day.events.length - 1].start).getTime() +
        day.events[day.events.length - 1].duration_h * 3600 * 1000
      ).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false })
    : "24:00";

  // Hour label
  const hourLabel = (h: number) => {
    if (h === 0) return "Mid-night";
    if (h === 12) return "Noon";
    return String(h);
  };

  // Recap values
  const r: DayLogRecap = day.recap || {
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
  const fmt = (n: number | undefined) => (n === undefined ? "—" : n.toFixed(2));

  // Recap layout
  const recapBodyTop = recapTop + 20;
  const recapBodyH = recapH - 20;
  const recapCellW = (W - 20) / 3;

  return (
    <div className="bg-white rounded-xl shadow-md p-4 my-4 print:shadow-none">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-sm font-semibold text-spotter-700">
          Driver's Daily Log — Day {index + 1} ({day.date})
        </h3>
        <span className="text-xs text-gray-500">{totalMiles.toFixed(0)} mi driven</span>
      </div>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-auto border border-gray-300 bg-white"
        style={{ fontFamily: "Inter, system-ui, sans-serif" }}
      >
        {/* Title bar */}
        <rect x={0} y={0} width={W} height={24} fill="#0e7c86" />
        <text x={W / 2} y={16} fill="white" fontSize={12} fontWeight={700} textAnchor="middle">
          DRIVERS DAILY LOG
        </text>

        {/* Date / 24 hours + Original/Duplicates banner */}
        <g fontSize={9} fill="#0b1f24">
          <text x={10} y={40} fontWeight={700} fontSize={11}>Drivers Daily Log</text>
          <text x={10} y={56}>
            <tspan fontWeight={700}>Date:</tspan> {day.date.replace(/-/g, " / ")} <tspan fontWeight={700}>(24 hours)</tspan>
          </text>
          <text x={10} y={72}>
            <tspan fontWeight={700}>From:</tspan> {fromTime}    <tspan fontWeight={700}>To:</tspan> {toTime}
          </text>
          <text x={10} y={88}>
            <tspan fontWeight={700}>Total Miles Driving Today:</tspan> {totalMiles.toFixed(0)}
          </text>
          <text x={300} y={88}>
            <tspan fontWeight={700}>Total Mileage Today:</tspan> {totalMileage.toFixed(0)}
          </text>
          <text x={10} y={104}>
            <tspan fontWeight={700}>Name of Carrier:</tspan> {carrierName}
          </text>
          <text x={300} y={104}>
            <tspan fontWeight={700}>Main Office Address:</tspan> {mainOffice}
          </text>
          {/* Original/Duplicates banner right side */}
          <text x={W - 12} y={40} textAnchor="end" fontWeight={700}>Original — File at home terminal.</text>
          <text x={W - 12} y={54} textAnchor="end" fontStyle="italic">Duplicates — retain for 8 days.</text>
          <text x={W - 12} y={72} textAnchor="end">
            <tspan fontWeight={700}>Truck/Trailer #:</tspan> {truckNumber}
          </text>
          <text x={W - 12} y={88} textAnchor="end">
            <tspan fontWeight={700}>Home Terminal:</tspan> {homeTerminal}
          </text>
          <text x={W - 12} y={104} textAnchor="end">
            <tspan fontWeight={700}>Co-Driver:</tspan> {coDriver || "—"}
          </text>
        </g>

        {/* Graph grid background */}
        <rect
          x={gridLeft}
          y={gridTop}
          width={gridW}
          height={gridH}
          fill="white"
          stroke="#1f2937"
          strokeWidth={1}
        />

        {/* Hour ticks + 15-min subdivs + hour label */}
        {Array.from({ length: 24 }).map((_, h) => (
          <g key={h}>
            <line
              x1={gridLeft + h * colHourW}
              y1={gridTop}
              x2={gridLeft + h * colHourW}
              y2={gridTop + gridH}
              stroke="#1f2937"
              strokeWidth={1}
            />
            {[0.25, 0.5, 0.75].map((f) => (
              <line
                key={f}
                x1={gridLeft + (h + f) * colHourW}
                y1={gridTop}
                x2={gridLeft + (h + f) * colHourW}
                y2={gridTop + gridH}
                stroke="#cbd5e1"
                strokeWidth={0.5}
              />
            ))}
            <text
              x={gridLeft + h * colHourW + colHourW / 2}
              y={xAxisTop + 13}
              fontSize={7}
              textAnchor="middle"
              fill="#0b1f24"
            >
              {hourLabel(h)}
            </text>
          </g>
        ))}
        <line
          x1={gridRight}
          y1={gridTop}
          x2={gridRight}
          y2={gridTop + gridH}
          stroke="#1f2937"
          strokeWidth={1}
        />

        {/* Mid-night / Total Hours column header */}
        <text
          x={gridLeft - 4}
          y={gridTop - 4}
          fontSize={7}
          textAnchor="end"
          fontWeight={700}
          fill="#0b1f24"
        >
          Mid-night
        </text>
        <text
          x={gridRight}
          y={gridTop - 4}
          fontSize={7}
          fontWeight={700}
          fill="#0b1f24"
        >
          Mid-night
        </text>

        {/* Horizontal row separators */}
        {[1, 2, 3].map((r) => (
          <line
            key={r}
            x1={gridLeft}
            y1={gridTop + r * rowH}
            x2={gridRight}
            y2={gridTop + r * rowH}
            stroke="#1f2937"
            strokeWidth={1}
          />
        ))}

        {/* Status labels on left */}
        {[0, 1, 2, 3].map((s) => (
          <text
            key={s}
            x={gridLeft - 8}
            y={gridTop + s * rowH + rowH / 2 + 3}
            fontSize={9}
            textAnchor="end"
            fontWeight={600}
            fill="#0b1f24"
          >
            {STATUS_LABELS[s as DutyStatus]}
          </text>
        ))}

        {/* Status quarter-hour fills */}
        {day.status_quarters.map((s, i) => {
          if (s === 0) return null;
          const x = gridLeft + i * (colHourW / 4);
          const w = colHourW / 4;
          return (
            <rect
              key={i}
              x={x}
              y={gridTop + s * rowH + 1}
              width={w}
              height={rowH - 2}
              fill={STATUS_COLORS[s as DutyStatus]}
              stroke={STATUS_COLORS[s as DutyStatus]}
              strokeWidth={0.5}
            />
          );
        })}

        {/* Total Hours column on right */}
        <rect
          x={totalColLeft}
          y={gridTop}
          width={totalColW}
          height={gridH}
          fill="white"
          stroke="#1f2937"
          strokeWidth={1}
        />
        <text
          x={totalColLeft + totalColW / 2}
          y={gridTop - 4}
          fontSize={8}
          fontWeight={700}
          textAnchor="middle"
          fill="#0b1f24"
        >
          Total Hours
        </text>
        {[
          { label: "Off", val: day.totals.off_duty },
          { label: "Sleeper", val: day.totals.sleeper },
          { label: "Driving", val: day.totals.driving },
          { label: "On Duty", val: day.totals.on_duty },
        ].map((row, i) => (
          <g key={i}>
            <text
              x={totalColLeft + 6}
              y={gridTop + i * rowH + 12}
              fontSize={7}
              fill="#0b1f24"
            >
              {row.label}
            </text>
            <text
              x={totalColLeft + totalColW - 6}
              y={gridTop + i * rowH + 12}
              fontSize={8}
              fontWeight={700}
              textAnchor="end"
              fill="#0b1f24"
            >
              {row.val.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Bottom rule under grid */}
        <line
          x1={gridLeft}
          y1={xAxisTop}
          x2={gridRight}
          y2={xAxisTop}
          stroke="#1f2937"
          strokeWidth={1}
        />

        {/* ── REMARKS (left) ── */}
        <rect
          x={remarksLeft}
          y={remarksTop}
          width={remarksMainW}
          height={remarksH}
          fill="white"
          stroke="#1f2937"
          strokeWidth={1}
        />
        <text x={remarksLeft + 8} y={remarksTop + 12} fontSize={9} fontWeight={700} fill="#0b1f24">
          REMARKS
        </text>
        {day.events
          .filter((e) => e.remark && e.remark !== "Driving" && !e.remark.includes("home terminal"))
          .slice(0, 8)
          .map((e, i) => {
            const time = new Date(e.start).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
              hour12: false,
            });
            const line = `${time} — ${e.location.label} — ${e.remark}`;
            return (
              <text
                key={i}
                x={remarksLeft + 8}
                y={remarksTop + 26 + i * 12}
                fontSize={8}
                fill="#0b1f24"
              >
                {line.length > 60 ? line.slice(0, 57) + "..." : line}
              </text>
            );
          })}

        {/* ── SHIPPING DOCUMENTS (right) ── */}
        <rect
          x={shippingLeft}
          y={remarksTop}
          width={shippingW}
          height={remarksH}
          fill="white"
          stroke="#1f2937"
          strokeWidth={1}
        />
        <text x={shippingLeft + 8} y={remarksTop + 12} fontSize={9} fontWeight={700} fill="#0b1f24">
          Shipping Documents
        </text>
        <text x={shippingLeft + 8} y={remarksTop + 28} fontSize={7} fill="#0b1f24">
          DVL or Manifest No. or
        </text>
        <text x={shippingLeft + 8} y={remarksTop + 50} fontSize={8} fontWeight={600} fill="#0b1f24">
          {shippingDoc}
        </text>
        <line
          x1={shippingLeft + 8}
          y1={remarksTop + 60}
          x2={shippingLeft + shippingW - 8}
          y2={remarksTop + 60}
          stroke="#cbd5e1"
          strokeWidth={0.5}
        />
        <text x={shippingLeft + 8} y={remarksTop + 78} fontSize={9} fontWeight={700} fill="#0b1f24">
          Shipper &amp; Commodity
        </text>
        <text x={shippingLeft + 8} y={remarksTop + 96} fontSize={8} fill="#0b1f24">
          {`${day.events.find((e) => e.remark === "Pickup")?.location.label || "—"}`}
        </text>
        <text x={shippingLeft + 8} y={remarksTop + 112} fontSize={8} fill="#0b1f24">
          General freight
        </text>

        {/* Italic caption under remarks */}
        <text x={gridLeft} y={italicTop + 12} fontSize={8} fontStyle="italic" fill="#475569">
          Enter name of place you reported and where released from work and when and where each change of duty occurred.
        </text>
        <text x={gridLeft} y={italicTop + 24} fontSize={8} fontStyle="italic" fill="#475569">
          Use time standard of home terminal.
        </text>

        {/* ════════════════ RECAP TABLE ════════════════ */}
        {/* Recap header bar */}
        <rect x={10} y={recapTop} width={W - 20} height={20} fill="#0e7c86" />
        <text x={20} y={recapTop + 14} fill="white" fontSize={10} fontWeight={700}>
          Recap (completed at end of day)
        </text>
        <text x={10 + recapCellW + 10} y={recapTop + 14} fill="white" fontSize={10} fontWeight={700}>
          70 Hour / 8 Day Drivers
        </text>
        <text x={10 + 2 * recapCellW + 10} y={recapTop + 14} fill="white" fontSize={10} fontWeight={700}>
          60 Hour / 7 Day Drivers
        </text>

        {/* Recap body (under header) */}
        <>
          {[recapCellW, recapCellW * 2].map((x) => (
            <line key={x} x1={x + 10} y1={recapBodyTop} x2={x + 10} y2={recapBodyTop + recapBodyH} stroke="#1f2937" strokeWidth={1} />
          ))}
          {/* 70/8 column: A, B, F */}
          <g fontSize={9} fill="#0b1f24">
            <text x={recapCellW + 20} y={recapBodyTop + 16} fontWeight={700}>A.</text>
            <text x={recapCellW + 36} y={recapBodyTop + 16}>Total hours on duty last 7 days</text>
            <text x={recapCellW + 36} y={recapBodyTop + 28}>including today</text>
            <text x={2 * recapCellW - 4} y={recapBodyTop + 16} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.last_7day_total)}
            </text>

            <text x={recapCellW + 20} y={recapBodyTop + 50} fontWeight={700}>B.</text>
            <text x={recapCellW + 36} y={recapBodyTop + 50}>Total hours available tomorrow</text>
            <text x={recapCellW + 36} y={recapBodyTop + 62}>(70 hr minus A)</text>
            <text x={2 * recapCellW - 4} y={recapBodyTop + 50} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.tomorrow_70_budget)}
            </text>

            <text x={recapCellW + 20} y={recapBodyTop + 90} fontWeight={700}>F.</text>
            <text x={recapCellW + 36} y={recapBodyTop + 90}>Total hours on duty last 8 days</text>
            <text x={recapCellW + 36} y={recapBodyTop + 102}>including today (lines 3 &amp; 4)</text>
            <text x={2 * recapCellW - 4} y={recapBodyTop + 90} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.last_8day_total)}
            </text>
          </g>

          {/* 60/7 column: C, D, E */}
          <g fontSize={9} fill="#0b1f24">
            <text x={2 * recapCellW + 20} y={recapBodyTop + 16} fontWeight={700}>C.</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 16}>Total hours on duty last 5 days</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 28}>including today</text>
            <text x={3 * recapCellW - 4} y={recapBodyTop + 16} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.last_5day_total)}
            </text>

            <text x={2 * recapCellW + 20} y={recapBodyTop + 50} fontWeight={700}>D.</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 50}>Total hours on duty last 7 days</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 62}>including today</text>
            <text x={3 * recapCellW - 4} y={recapBodyTop + 50} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.last_7day_total_60)}
            </text>

            <text x={2 * recapCellW + 20} y={recapBodyTop + 90} fontWeight={700}>E.</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 90}>Total hours available tomorrow</text>
            <text x={2 * recapCellW + 36} y={recapBodyTop + 102}>(60 hr minus C)</text>
            <text x={3 * recapCellW - 4} y={recapBodyTop + 90} textAnchor="end" fontWeight={700} fontSize={11}>
              {fmt(r.tomorrow_60_budget)}
            </text>
          </g>

          {/* Left column: "On duty hours / Total lines 3 & 4" mini table */}
          <rect x={10} y={recapBodyTop} width={recapCellW} height={recapBodyH} fill="white" />
          <text x={20} y={recapBodyTop + 16} fontSize={9} fontWeight={700} fill="#0b1f24">
            On duty hours
          </text>
          <text x={20} y={recapBodyTop + 30} fontSize={8} fontStyle="italic" fill="#475569">
            (Total lines 3 &amp; 4)
          </text>
          <line x1={20} y1={recapBodyTop + 40} x2={recapCellW - 10} y2={recapBodyTop + 40} stroke="#cbd5e1" strokeWidth={0.5} />
          <text x={20} y={recapBodyTop + 60} fontSize={9} fill="#0b1f24">Today:</text>
          <text x={recapCellW - 6} y={recapBodyTop + 60} fontSize={11} fontWeight={700} textAnchor="end" fill="#0b1f24">
            {fmt((day.totals.driving + day.totals.on_duty))}
          </text>
          <text x={20} y={recapBodyTop + 90} fontSize={8} fontStyle="italic" fill="#475569">
            {r.approximate ? "Approx. — see note" : ""}
          </text>

          {/* 34-hr restart banner — bottom of recap if applicable */}
          {r.took_34h_restart ? (
            <g>
              <rect
                x={W - 20 - sidebarCol}
                y={recapBodyTop + 130}
                width={sidebarCol}
                height={60}
                fill="#fef3c7"
                stroke="#92400e"
                strokeWidth={1}
                rx={4}
              />
              <text x={W - 20 - sidebarCol + 8} y={recapBodyTop + 148} fontSize={9} fontWeight={700} fill="#92400e">
                34-hr restart
              </text>
              <text x={W - 20 - sidebarCol + 8} y={recapBodyTop + 164} fontSize={7} fill="#78350f">
                taken on this day
              </text>
              <text x={W - 20 - sidebarCol + 8} y={recapBodyTop + 180} fontSize={7} fill="#78350f">
                → 60/70 hrs available
              </text>
            </g>
          ) : null}
        </>

        {/* Sidebar note (bottom of recap) */}
        <text x={W - 20} y={recapTop + recapH - 6} fontSize={7} fontStyle="italic" textAnchor="end" fill="#475569">
          * If you took 34 consecutive hours off duty you have 60/70 hours available
        </text>

        {/* Footer: certification + shipping doc */}
        <line x1={10} y1={recapTop + recapH + 8} x2={W - 10} y2={recapTop + recapH + 8} stroke="#cbd5e1" strokeWidth={0.5} />
        <g fontSize={8} fill="#475569">
          <text x={10} y={recapTop + recapH + 22}>
            I certify that these entries are true and correct — {driverName}
          </text>
          <text x={W - 10} y={recapTop + recapH + 22} textAnchor="end">
            Shipping Doc: {shippingDoc}
          </text>
        </g>
      </svg>
    </div>
  );
}
