import { useEffect, useState, type FormEvent } from "react";
import { fetchVehicles, createVehicle, updateVehicle } from "../lib/api";
import type { Vehicle } from "../lib/types";
import { Truck, Plus, Loader2, X } from "lucide-react";

export function VehiclesPage() {
  const [vehicles, setVehicles] = useState<Vehicle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Vehicle | null>(null);
  const [form, setForm] = useState({ plate: "", make: "", model: "", fuel_consumption_rate_l_100km: "", tank_capacity_l: "", status: "active" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await fetchVehicles();
      setVehicles(r.vehicles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchVehicles().then(r => setVehicles(r.vehicles)).catch(e => setError(e instanceof Error ? e.message : "")).finally(() => setLoading(false));
  }, []);

  function openCreate() {
    setEditing(null);
    setForm({ plate: "", make: "", model: "", fuel_consumption_rate_l_100km: "", tank_capacity_l: "", status: "active" });
    setShowForm(true);
  }

  function openEdit(v: Vehicle) {
    setEditing(v);
    setForm({
      plate: v.plate, make: v.make, model: v.model,
      fuel_consumption_rate_l_100km: String(v.fuel_consumption_rate_l_100km),
      tank_capacity_l: String(v.tank_capacity_l),
      status: v.status,
    });
    setShowForm(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const data: Partial<Vehicle> = {
        plate: form.plate,
        make: form.make,
        model: form.model,
        fuel_consumption_rate_l_100km: Number(form.fuel_consumption_rate_l_100km) || 0,
        tank_capacity_l: Number(form.tank_capacity_l) || 0,
        status: form.status as Vehicle["status"],
      };
      if (editing) {
        await updateVehicle(editing.id, data);
      } else {
        await createVehicle(data);
      }
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-spotter-800">Vehicles</h2>
          <p className="text-sm text-gray-500">{vehicles.length} in fleet</p>
        </div>
        <button onClick={openCreate} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700">
          <Plus className="w-4 h-4" /> Add Vehicle
        </button>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">{error}</div>}

      {showForm && (
        <form onSubmit={handleSave} className="bg-white rounded-xl shadow-md p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">{editing ? "Edit Vehicle" : "New Vehicle"}</h3>
            <button type="button" onClick={() => setShowForm(false)}><X className="w-4 h-4 text-gray-400" /></button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div><label className="text-xs font-medium text-gray-600">Plate *</label><input required value={form.plate} onChange={e => setForm({ ...form, plate: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Make</label><input value={form.make} onChange={e => setForm({ ...form, make: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Model</label><input value={form.model} onChange={e => setForm({ ...form, model: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Status</label>
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm">
                <option value="active">Active</option><option value="maintenance">Maintenance</option><option value="retired">Retired</option>
              </select></div>
            <div><label className="text-xs font-medium text-gray-600">L/100km</label><input type="number" step="0.1" value={form.fuel_consumption_rate_l_100km} onChange={e => setForm({ ...form, fuel_consumption_rate_l_100km: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Tank (L)</label><input type="number" step="1" value={form.tank_capacity_l} onChange={e => setForm({ ...form, tank_capacity_l: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
          </div>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700 disabled:opacity-50">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
          </button>
        </form>
      )}

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        {vehicles.length === 0 && !loading ? (
          <div className="p-10 text-center text-gray-400"><Truck className="w-10 h-10 mx-auto text-spotter-200 mb-3" /><p className="text-sm">No vehicles</p></div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 uppercase border-b bg-spotter-50/50">
              <tr>
                <th className="text-left py-2 px-4">Plate</th>
                <th className="text-left py-2 px-4">Make/Model</th>
                <th className="text-right py-2 px-4">L/100km</th>
                <th className="text-right py-2 px-4">Tank</th>
                <th className="text-right py-2 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map(v => (
                <tr key={v.id} className="border-b last:border-0 hover:bg-spotter-50/30 cursor-pointer" onClick={() => openEdit(v)}>
                  <td className="py-2 px-4 font-medium text-spotter-700">{v.plate}</td>
                  <td className="py-2 px-4 text-gray-600">{v.make} {v.model}</td>
                  <td className="py-2 px-4 text-right">{v.fuel_consumption_rate_l_100km}</td>
                  <td className="py-2 px-4 text-right">{v.tank_capacity_l}L</td>
                  <td className="py-2 px-4 text-right">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${v.status === "active" ? "bg-green-100 text-green-800" : v.status === "maintenance" ? "bg-amber-100 text-amber-800" : "bg-gray-100 text-gray-800"}`}>{v.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
