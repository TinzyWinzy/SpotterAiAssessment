export interface Point {
  lat: number;
  lon: number;
  label: string;
}

export interface RouteInfo {
  distance_km: number;
  duration_h: number;
  geometry: {
    type: "LineString";
    coordinates: [number, number][];
  };
}

export interface StopMarker {
  lat: number;
  lon: number;
  label: string;
  kind: "origin" | "waypoint" | "destination";
}

export interface CostBreakdown {
  route_distance_km: number;
  estimated_days: number;
  fuel_cost_usd: number;
  driver_pay_usd: number;
  border_fees_usd: number;
  tolls_usd: number;
  maintenance_provision_usd: number;
  total_cost_usd: number;
  break_even_revenue_usd: number;
  recommended_revenue_usd: number;
  profit_margin_pct: number;
}

export interface TripRequest {
  origin: string;
  destination: string;
  waypoints?: string[];
  driver_id?: number;
  vehicle_id?: number;
  commodity_id?: number;
  load_weight_tonnes?: number;
  estimated_revenue?: number;
}

export interface TripEstimateRequest {
  origin: string;
  destination: string;
  waypoints?: string[];
  vehicle_id?: number;
  driver_id?: number;
  fuel_price_per_litre_usd?: number;
  border_crossings?: number;
  tolls_usd?: number;
}

export interface TripResponse {
  ok: boolean;
  stops: StopMarker[];
  route: RouteInfo;
  driver_id: number | null;
  vehicle_id: number | null;
  trip_id?: number;
  cost_estimate?: CostBreakdown;
}

export interface TripEstimateResponse {
  ok: boolean;
  route: RouteInfo;
  cost_estimate: CostBreakdown;
}

// --- Commodities ---

export interface CommodityCategory {
  id: number;
  name: string;
  icon: string;
}

export interface Commodity {
  id: number;
  name: string;
  category: number;
  category_name: string;
  category_icon: string;
  unit: string;
  rate_per_km: number | null;
  rate_per_kg: number | null;
  flat_fee: number | null;
  is_active: boolean;
}

// --- Models ---

export interface Organisation {
  id: number;
  name: string;
  slug: string;
  licensed_vehicles: number;
  contact_phone: string;
  contact_email: string;
}

export interface Vehicle {
  id: number;
  organisation: number;
  organisation_name: string;
  plate: string;
  make: string;
  model: string;
  year: number | null;
  fuel_type: "diesel" | "petrol";
  fuel_consumption_rate_l_100km: number;
  tank_capacity_l: number;
  service_interval_km: number;
  last_service_km: number;
  current_odometer_km: number;
  status: "active" | "maintenance" | "retired";
  created_at: string;
}

export interface Driver {
  id: number;
  organisation: number | null;
  organisation_name: string;
  user: number | null;
  name: string;
  phone_number: string;
  licence_number: string;
  licence_expiry: string | null;
  rate_per_day_usd: number;
  rate_per_km_usd: number;
  status: "active" | "inactive";
  created_at: string;
}

export interface Trip {
  id: number;
  organisation: number | null;
  vehicle: number | null;
  vehicle_plate: string | null;
  driver: number | null;
  driver_name: string | null;
  service_type: string;
  booking_reference: string | null;
  customer_name: string;
  customer_phone: string;
  customer_email: string;
  customer_token: string | null;
  booking_time_preference: BookingTimePreference | null;
  cargo_items: CargoItem[];
  truck_recommendation: TruckRecommendation | null;
  origin: string;
  destination: string;
  waypoints: string[];
  distance_km: number;
  origin_address: string;
  destination_address: string;
  pickup_notes: string;
  delivery_notes: string;
  scheduled_start: string | null;
  actual_start: string | null;
  actual_end: string | null;
  estimated_fuel_cost_usd: number;
  estimated_driver_pay_usd: number;
  estimated_border_fees_usd: number;
  estimated_tolls_usd: number;
  estimated_total_cost_usd: number;
  actual_fuel_cost_usd: number | null;
  actual_driver_pay_usd: number | null;
  actual_border_fees_usd: number | null;
  actual_total_cost_usd: number | null;
  revenue_usd: number | null;
  estimated_revenue: number | null;
  route_geometry: { type: "LineString"; coordinates: [number, number][] } | null;
  status: TripStatus;
  priority: "low" | "normal" | "high" | "urgent";
  load_type: string;
  load_weight_tonnes: number | null;
  commodity: number | null;
  commodity_data: Commodity | null;
  notes: string;
  created_at: string;
  updated_at: string;
  sos_triggered_at: string | null;
  sos_acknowledged_at: string | null;
  sos_message: string;
  status_logs?: TripStatusLog[];
}

export interface CargoItem {
  description: string;
  quantity: number;
  estimated_weight_kg: number;
  dimensions?: string;
  is_fragile: boolean;
  needs_packing: boolean;
  needs_lifting: boolean;
}

export interface BookingTimePreference {
  date?: string;
  time_slot?: "morning" | "afternoon" | "evening";
}

export interface TruckRecommendation {
  recommended_size: string;
  capacity_tonnes: number;
  explanation: string;
  alternatives: string[];
}

export interface ServiceType {
  key: string;
  name: string;
  description: string;
  icon: string;
  default_truck_sizes: string[];
}

export interface PublicQuoteRequest {
  service_type: string;
  origin: string;
  destination: string;
  waypoints?: string[];
  cargo_items?: CargoItem[];
  has_fragile?: boolean;
  needs_packing?: boolean;
  needs_labour?: boolean;
  floor_count?: number;
}

export interface PublicBookingRequest {
  service_type: string;
  origin: string;
  destination: string;
  waypoints?: string[];
  cargo_items?: CargoItem[];
  booking_time_preference?: BookingTimePreference;
  has_fragile?: boolean;
  needs_packing?: boolean;
  needs_labour?: boolean;
  floor_count?: number;
  customer_name?: string;
  customer_phone?: string;
  customer_email?: string;
  pickup_notes?: string;
  delivery_notes?: string;
}

export interface PublicQuoteResponse {
  ok: boolean;
  route: RouteInfo;
  truck_recommendation: TruckRecommendation;
  cost_estimate: {
    route_distance_km: number;
    base_fee_usd: number;
    distance_fee_usd: number;
    loading_fee_usd: number;
    packing_fee_usd: number;
    fragile_surcharge_usd: number;
    floor_fee_usd: number;
    fuel_surcharge_usd: number;
    total_estimated_usd: number;
  };
}

export interface PublicBookingResponse {
  ok: boolean;
  booking_reference: string;
  customer_token: string;
  tracking_url: string;
  trip_id: number;
  truck_recommendation: {
    recommended_size: string;
    capacity_tonnes: number;
    explanation: string;
  };
  cost_estimate: {
    total_estimated_usd: number;
  };
}

export interface TrackingData {
  ok: boolean;
  booking_reference: string;
  status: TripStatus;
  service_type: string;
  origin: string;
  destination: string;
  origin_address: string;
  destination_address: string;
  distance_km: number;
  estimated_total_cost_usd: number;
  driver_name: string | null;
  driver_phone: string | null;
  vehicle_plate: string | null;
  truck_recommendation: TruckRecommendation | null;
  cargo_items: CargoItem[];
  pickup_notes: string;
  delivery_notes: string;
  status_logs: TripStatusLog[];
  last_position: TripPosition | null;
  created_at: string;
  updated_at: string;
}

export interface TripImage {
  id: number;
  trip: number;
  image: string;
  caption: string;
  uploaded_at: string;
  uploaded_by: number | null;
}

export type TripStatus = "inquiry" | "quoted" | "confirmed" | "assigned" | "dispatched" | "at_border" | "in_transit" | "delivered" | "paid" | "cancelled";

export interface TripStatusLog {
  id: number;
  trip: number;
  from_status: string;
  to_status: string;
  location_text: string;
  notes: string;
  timestamp: string;
  updated_by: number | null;
  updated_by_name: string | null;
}

export interface TripPosition {
  id: number;
  trip: number;
  lat: number;
  lon: number;
  accuracy: number | null;
  source: "manual" | "gps" | "whatsapp";
  remark: string;
  timestamp: string;
  reported_by: number | null;
  reported_by_name: string | null;
}

export interface FuelRecord {
  id: number;
  trip: number;
  vehicle: number;
  litres: number;
  price_per_litre_usd: number;
  total_cost_usd: number;
  location_text: string;
  created_at: string;
}

// --- Auth ---

export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  driver_id: number | null;
}

// --- Admin ---

export interface DashboardMetrics {
  ok: true;
  generated_at: string;
  date_range: { from: string | null; to: string | null };
  totals: {
    trips: number;
    drivers: number;
    vehicles: number;
    active_vehicles: number;
    vehicles_with_trips: number;
    km: number;
    avg_km_per_trip: number;
    revenue_usd: number;
    estimated_cost_usd: number;
    actual_cost_usd: number | null;
    estimated_profit_usd: number;
    actual_profit_usd: number | null;
  };
  fuel: {
    total_litres: number;
    total_cost_usd: number;
    fleet_efficiency_l_100km: number;
    records: number;
  };
  status_distribution: Record<string, number>;
  window: {
    trips_7d: number;
    trips_30d: number;
    sparkline_30d: { date: string; count: number }[];
  };
  comparison: {
    trips_this_month: number;
    trips_last_month: number;
    revenue_this_month_usd: number;
    revenue_last_month_usd: number;
  };
  top_routes: { origin: string; destination: string; count: number; km: number }[];
  top_drivers: { id: number; name: string; trips: number; km: number }[];
  top_vehicles: { id: number; plate: string; trips: number; km: number }[];
}
