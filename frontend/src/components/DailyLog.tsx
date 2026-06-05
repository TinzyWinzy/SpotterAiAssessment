import type { DayLog, DutyStatus } from "../lib/types";

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
  index: number;
}

export function DailyLog({
  day,
  carrierName = "John Doe's Transportation",
  mainOffice = "Washington, D.C.",
  truckNumber = "123, 20544",
  shippingDoc = "101601",
  coDriver = "",
  driverName = "Tinotenda Duma",
  index,
}: Props) {
  const W = 900;
  const H = 620;

  // Grid layout
  const headerH = 90;
  const gridTop = headerH;
  const gridLeft = 130;
  const gridRight = W - 80;
  const gridW = gridRight - gridLeft;
  const colHourW = gridW / 24;
  const rowH = 36;
  const gridH = rowH * 4;
  const xAxisTop = gridTop + gridH;
  const xAxisH = 22;
  const totalColLeft = gridRight;
  const totalColW = 70;
  const remarksTop = xAxisTop + xAxisH + 12;
  const remarksH = 110;
  const footerTop = remarksTop + remarksH + 8;

  // Compute total miles from events
  const totalMiles = day.total_miles;

  // Format hour label
  const hourLabel = (h: number) => {
    if (h === 0) return "Midnight";
    if (h === 12) return "Noon";
    return String(h);
  };

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
        {/* Header — Title bar */}
        <rect x={0} y={0} width={W} height={26} fill="#0e7c86" />
        <text x={W / 2} y={18} fill="white" fontSize={14} fontWeight={700} textAnchor="middle">
          U.S. DEPARTMENT OF TRANSPORTATION — DRIVER'S DAILY LOG (ONE CALENDAR DAY — 24 HOURS)
        </text>

        {/* Header — Form fields */}
        <g fontSize={9} fill="#0b1f24">
          <text x={10} y={42}>
            <tspan fontWeight={700}>Date:</tspan> {day.date}
          </text>
          <text x={210} y={42}>
            <tspan fontWeight={700}>Total Miles Driving Today:</tspan> {totalMiles.toFixed(0)}
          </text>
          <text x={10} y={58}>
            <tspan fontWeight={700}>Name of Carrier:</tspan> {carrierName}
          </text>
          <text x={430} y={58}>
            <tspan fontWeight={700}>Main Office Address:</tspan> {mainOffice}
          </text>
          <text x={10} y={74}>
            <tspan fontWeight={700}>Vehicle Numbers:</tspan> {truckNumber}
          </text>
          <text x={430} y={74}>
            <tspan fontWeight={700}>Co-Driver:</tspan> {coDriver || "—"}
          </text>
          <text x={10} y={88} fontSize={8} fill="#475569">
            I certify that these entries are true and correct — {driverName}
          </text>
          <text x={430} y={88} fontSize={8} fill="#475569">
            Shipping Doc: {shippingDoc}
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

        {/* Hour ticks + vertical quarter-hour lines */}
        {Array.from({ length: 24 }).map((_, h) => (
          <g key={h}>
            {/* Hour line */}
            <line
              x1={gridLeft + h * colHourW}
              y1={gridTop}
              x2={gridLeft + h * colHourW}
              y2={gridTop + gridH}
              stroke="#1f2937"
              strokeWidth={1}
            />
            {/* 15-min subdivs */}
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
            {/* Hour label */}
            <text
              x={gridLeft + h * colHourW + colHourW / 2}
              y={xAxisTop + 14}
              fontSize={8}
              textAnchor="middle"
              fill="#0b1f24"
            >
              {hourLabel(h)}
            </text>
          </g>
        ))}
        {/* Right boundary */}
        <line
          x1={gridRight}
          y1={gridTop}
          x2={gridRight}
          y2={gridTop + gridH}
          stroke="#1f2937"
          strokeWidth={1}
        />

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
            fontSize={10}
            textAnchor="end"
            fontWeight={600}
            fill="#0b1f24"
          >
            {STATUS_LABELS[s as DutyStatus]}
          </text>
        ))}

        {/* Status quarter-hour fills */}
        {day.status_quarters.map((s, i) => {
          if (s === 0) return null; // off duty = no fill
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

        {/* Total Hours column */}
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
          fontSize={9}
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
              y={gridTop + i * rowH + 14}
              fontSize={8}
              fill="#0b1f24"
            >
              {row.label}
            </text>
            <text
              x={totalColLeft + totalColW - 6}
              y={gridTop + i * rowH + 14}
              fontSize={9}
              fontWeight={700}
              textAnchor="end"
              fill="#0b1f24"
            >
              {row.val.toFixed(2)}
            </text>
          </g>
        ))}

        {/* Bottom rule */}
        <line
          x1={gridLeft}
          y1={xAxisTop}
          x2={gridRight}
          y2={xAxisTop}
          stroke="#1f2937"
          strokeWidth={1}
        />

        {/* Remarks section */}
        <rect
          x={gridLeft}
          y={remarksTop}
          width={W - gridLeft - 10}
          height={remarksH}
          fill="white"
          stroke="#1f2937"
          strokeWidth={1}
        />
        <text x={gridLeft + 8} y={remarksTop + 14} fontSize={10} fontWeight={700} fill="#0b1f24">
          REMARKS
        </text>
        {day.events
          .filter((e) => e.remark && e.remark !== "Driving" && !e.remark.includes("home terminal"))
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
                x={gridLeft + 8}
                y={remarksTop + 30 + i * 14}
                fontSize={9}
                fill="#0b1f24"
              >
                {line}
              </text>
            );
          })}

        {/* Footer recap */}
        <g fontSize={9} fill="#0b1f24">
          <text x={10} y={footerTop + 14} fontWeight={700}>
            Recap (completed at end of day)
          </text>
          <text x={10} y={footerTop + 30}>
            On duty hours today: {day.totals.on_duty.toFixed(2)} | Driving: {day.totals.driving.toFixed(2)} | Off: {day.totals.off_duty.toFixed(2)} | Sleeper: {day.totals.sleeper.toFixed(2)}
          </text>
          <text x={10} y={footerTop + 46}>
            70-Hour / 8-Day Drivers: A. Total hours on duty last 7 days including today — (rolling 8-day total tracked across days)
          </text>
        </g>
      </svg>
    </div>
  );
}
