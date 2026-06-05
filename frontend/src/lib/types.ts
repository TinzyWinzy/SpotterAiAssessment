export type DutyStatus = 0 | 1 | 2 | 3;

export const STATUS_NAMES: Record<DutyStatus, string> = {
  0: "Off Duty",
  1: "Sleeper Berth",
  2: "Driving",
  3: "On Duty (Not Driving)",
};

export interface Point {
  lat: number;
  lon: number;
  label: string;
}

export interface RouteInfo {
  distance_mi: number;
  duration_h: number;
  geometry: {
    type: "LineString";
    coordinates: [number, number][]; // [lon, lat] per GeoJSON
  };
}

export interface StopMarker {
  lat: number;
  lon: number;
  label: string;
  kind: "current" | "pickup" | "dropoff";
}

export interface RestStopMarker {
  lat: number;
  lon: number;
  label: string;
  kind: "fuel" | "break" | "rest" | "pickup" | "dropoff";
  remark: string;
  day: string;
  duration_h: number;
  cumulative_miles: number;
}

export interface TripEvent {
  start: string;
  duration_h: number;
  status: DutyStatus;
  status_name: string;
  location: Point;
  remark: string;
  cumulative_miles: number;
}

export interface DayLog {
  date: string;
  total_miles: number;
  events: TripEvent[];
  totals: { off_duty: number; sleeper: number; driving: number; on_duty: number };
  status_quarters: DutyStatus[];
}

export interface TripRequest {
  current_location: string;
  pickup_location: string;
  dropoff_location: string;
  current_cycle_used_hrs: number;
  use_sleeper_berth?: boolean;
  avg_speed_mph?: number;
  start_time?: string;
}

export interface TripResponse {
  ok: boolean;
  stops: StopMarker[];
  rest_stops: RestStopMarker[];
  route: RouteInfo;
  total_distance_mi: number;
  days: DayLog[];
  cycle_used_hrs: number;
  warnings: string[];
}
