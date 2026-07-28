import { useState, useEffect, useCallback } from "react";
import { reportTripPosition, updateTripStatus } from "./api";

interface QueuedPosition {
  tripId: number;
  lat: number;
  lon: number;
  accuracy?: number;
  source: string;
  timestamp: string;
}

interface QueuedStatus {
  tripId: number;
  status: string;
  timestamp: string;
}

type QueueItem =
  | { type: "position"; data: QueuedPosition }
  | { type: "status"; data: QueuedStatus };

function readQueue(): QueueItem[] {
  try {
    return JSON.parse(localStorage.getItem("offline_queue") || "[]");
  } catch {
    return [];
  }
}

export function useOfflineSync() {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [pendingCount, setPendingCount] = useState(() => readQueue().length);

  const syncNow = useCallback(async () => {
    if (!navigator.onLine) return;
    const queue = readQueue();
    if (queue.length === 0) return;

    const remaining: QueueItem[] = [];
    for (const item of queue) {
      try {
        if (item.type === "position") {
          await reportTripPosition(item.data.tripId, {
            lat: item.data.lat,
            lon: item.data.lon,
            accuracy: item.data.accuracy,
            source: item.data.source,
          });
        } else if (item.type === "status") {
          await updateTripStatus(item.data.tripId, item.data.status);
        }
      } catch {
        remaining.push(item);
      }
    }
    localStorage.setItem("offline_queue", JSON.stringify(remaining));
    setPendingCount(remaining.length);
  }, []);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncNow();
    };
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [syncNow]);

  return { isOnline, pendingCount, syncNow };
}
