import type { TripStatusLog } from "../lib/types";
import { Clock } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  dispatched: "bg-blue-500",
  at_border: "bg-amber-500",
  in_transit: "bg-purple-500",
  delivered: "bg-green-500",
  paid: "bg-emerald-500",
  cancelled: "bg-red-500",
};

const STATUS_LABELS: Record<string, string> = {
  dispatched: "Dispatched",
  at_border: "At Border",
  in_transit: "In Transit",
  delivered: "Delivered",
  paid: "Paid",
  cancelled: "Cancelled",
};

export function StatusTimeline({ logs }: { logs: TripStatusLog[] }) {
  if (logs.length === 0) {
    return <p className="text-xs text-gray-400">No status updates yet.</p>;
  }

  return (
    <div className="relative">
      {logs.map((log, i) => {
        const isLast = i === logs.length - 1;
        const color = STATUS_COLORS[log.to_status] || "bg-gray-400";
        return (
          <div key={log.id} className="flex gap-3 pb-4 relative">
            {!isLast && <div className="absolute left-[11px] top-5 bottom-0 w-0.5 bg-gray-200" />}
            <div className={`mt-1 w-[22px] h-[22px] rounded-full flex-shrink-0 flex items-center justify-center ${color}`}>
              <div className="w-2 h-2 rounded-full bg-white" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-900 capitalize">
                  {STATUS_LABELS[log.to_status] || log.to_status.replace(/_/g, " ")}
                </span>
                <span className="text-[10px] text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {new Date(log.timestamp).toLocaleString()}
                </span>
              </div>
              {(log.location_text || log.notes) && (
                <p className="text-xs text-gray-500 mt-0.5">
                  {[log.location_text, log.notes].filter(Boolean).join(" — ")}
                </p>
              )}
              {log.updated_by_name && (
                <p className="text-[10px] text-gray-400 mt-0.5">by {log.updated_by_name}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
