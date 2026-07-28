import { useEffect, useState, type FormEvent } from "react";
import { fetchDrivers, createDriver, updateDriver } from "../lib/api";
import type { Driver } from "../lib/types";
import { Users, Plus, Loader2, X } from "lucide-react";

export function DriversPage() {
  const [drivers, setDrivers] = useState<Driver[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Driver | null>(null);
  const [form, setForm] = useState({ name: "", phone_number: "", licence_number: "", rate_per_day_usd: "", rate_per_km_usd: "", status: "active" });
  const [saving, setSaving] = useState(false);

  async function load() {
    setLoading(true);
    try {
      const r = await fetchDrivers();
      setDrivers(r.drivers);
    } catch (e) {
      setError(e instanceof Error ? e.message : "");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchDrivers().then(r => setDrivers(r.drivers)).catch(e => setError(e instanceof Error ? e.message : "")).finally(() => setLoading(false));
  }, []);

  function openCreate() {
    setEditing(null);
    setForm({ name: "", phone_number: "", licence_number: "", rate_per_day_usd: "", rate_per_km_usd: "", status: "active" });
    setShowForm(true);
  }

  function openEdit(d: Driver) {
    setEditing(d);
    setForm({
      name: d.name, phone_number: d.phone_number, licence_number: d.licence_number,
      rate_per_day_usd: String(d.rate_per_day_usd), rate_per_km_usd: String(d.rate_per_km_usd),
      status: d.status,
    });
    setShowForm(true);
  }

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const data: Partial<Driver> = {
        name: form.name,
        phone_number: form.phone_number,
        licence_number: form.licence_number,
        rate_per_day_usd: Number(form.rate_per_day_usd) || 0,
        rate_per_km_usd: Number(form.rate_per_km_usd) || 0,
        status: form.status as Driver["status"],
      };
      if (editing) {
        await updateDriver(editing.id, data);
      } else {
        await createDriver(data);
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
          <h2 className="text-xl font-bold text-spotter-800">Drivers</h2>
          <p className="text-sm text-gray-500">{drivers.length} drivers</p>
        </div>
        <button onClick={openCreate} className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700">
          <Plus className="w-4 h-4" /> Add Driver
        </button>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-800">{error}</div>}

      {showForm && (
        <form onSubmit={handleSave} className="bg-white rounded-xl shadow-md p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold">{editing ? "Edit Driver" : "New Driver"}</h3>
            <button type="button" onClick={() => setShowForm(false)}><X className="w-4 h-4 text-gray-400" /></button>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div><label className="text-xs font-medium text-gray-600">Name *</label><input required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Phone</label><input value={form.phone_number} onChange={e => setForm({ ...form, phone_number: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Licence #</label><input value={form.licence_number} onChange={e => setForm({ ...form, licence_number: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Rate/day ($)</label><input type="number" step="0.01" value={form.rate_per_day_usd} onChange={e => setForm({ ...form, rate_per_day_usd: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Rate/km ($)</label><input type="number" step="0.01" value={form.rate_per_km_usd} onChange={e => setForm({ ...form, rate_per_km_usd: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm" /></div>
            <div><label className="text-xs font-medium text-gray-600">Status</label>
              <select value={form.status} onChange={e => setForm({ ...form, status: e.target.value })} className="w-full mt-1 px-2 py-1.5 border rounded text-sm">
                <option value="active">Active</option><option value="inactive">Inactive</option>
              </select></div>
          </div>
          <button type="submit" disabled={saving} className="px-4 py-1.5 text-sm bg-spotter-600 text-white rounded-md hover:bg-spotter-700 disabled:opacity-50">
            {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : "Save"}
          </button>
        </form>
      )}

      <div className="bg-white rounded-xl shadow-md overflow-hidden">
        {drivers.length === 0 && !loading ? (
          <div className="p-10 text-center text-gray-400"><Users className="w-10 h-10 mx-auto text-spotter-200 mb-3" /><p className="text-sm">No drivers</p></div>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 uppercase border-b bg-spotter-50/50">
              <tr>
                <th className="text-left py-2 px-4">Name</th>
                <th className="text-left py-2 px-4">Phone</th>
                <th className="text-left py-2 px-4">Licence</th>
                <th className="text-right py-2 px-4">$/day</th>
                <th className="text-right py-2 px-4">$/km</th>
                <th className="text-right py-2 px-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map(d => (
                <tr key={d.id} className="border-b last:border-0 hover:bg-spotter-50/30 cursor-pointer" onClick={() => openEdit(d)}>
                  <td className="py-2 px-4 font-medium text-spotter-700">{d.name}</td>
                  <td className="py-2 px-4 text-gray-600">{d.phone_number}</td>
                  <td className="py-2 px-4 text-gray-500">{d.licence_number}</td>
                  <td className="py-2 px-4 text-right">{d.rate_per_day_usd.toFixed(2)}</td>
                  <td className="py-2 px-4 text-right">{d.rate_per_km_usd.toFixed(2)}</td>
                  <td className="py-2 px-4 text-right">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium capitalize ${d.status === "active" ? "bg-green-100 text-green-800" : "bg-gray-100 text-gray-800"}`}>{d.status}</span>
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
