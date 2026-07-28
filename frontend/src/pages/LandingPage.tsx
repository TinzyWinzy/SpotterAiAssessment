import { useNavigate } from "react-router-dom";
import { Truck, MapPin, MessageCircle, AlertTriangle, BarChart3, Smartphone, ArrowRight, Menu, X } from "lucide-react";
import { useState } from "react";

const features = [
  { icon: MessageCircle, title: "WhatsApp Concierge", desc: "Drivers send location, update status, and trigger SOS via WhatsApp. No app install needed." },
  { icon: MapPin, title: "Live GPS Tracking", desc: "Phone-based GPS tracking with offline queue. No hardware trackers required." },
  { icon: AlertTriangle, title: "SOS & Safety", desc: "Panic button alerts dispatchers instantly. Know when your driver needs help." },
  { icon: Smartphone, title: "Driver PWA", desc: "Installable web app works offline. Background location updates even with the screen off." },
  { icon: BarChart3, title: "Dispatch Dashboard", desc: "Real-time map of all active trips. See vehicle positions, status, and SOS alerts at a glance." },
  { icon: Truck, title: "Cross-Border Routes", desc: "Built for SADC corridors — Harare-Joburg, Bulawayo-Gaborone, Mutare-Beira and more." },
];

export function LandingPage() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-spotter-600 flex items-center justify-center">
              <Truck className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-bold text-gray-900">Trucki</span>
          </div>
          <div className="hidden sm:flex items-center gap-6 text-sm">
            <a href="#features" className="text-gray-600 hover:text-spotter-600">Features</a>
            <a href="#how-it-works" className="text-gray-600 hover:text-spotter-600">How it works</a>
            <a href="#contact" className="text-gray-600 hover:text-spotter-600">Contact</a>
            <button onClick={() => navigate("/login")} className="text-gray-600 hover:text-spotter-600 font-medium">Sign in</button>
            <button onClick={() => navigate("/login")} className="bg-spotter-600 hover:bg-spotter-700 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition">Get early access</button>
          </div>
          <button className="sm:hidden p-1" onClick={() => setMenuOpen(!menuOpen)}>
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
        {menuOpen && (
          <div className="sm:hidden border-t border-gray-100 px-4 py-3 space-y-2 bg-white">
            <a href="#features" onClick={() => setMenuOpen(false)} className="block text-sm text-gray-600 py-1">Features</a>
            <a href="#how-it-works" onClick={() => setMenuOpen(false)} className="block text-sm text-gray-600 py-1">How it works</a>
            <a href="#contact" onClick={() => setMenuOpen(false)} className="block text-sm text-gray-600 py-1">Contact</a>
            <hr className="my-1" />
            <button onClick={() => { setMenuOpen(false); navigate("/login"); }} className="block text-sm text-spotter-600 font-medium py-1">Sign in</button>
            <button onClick={() => { setMenuOpen(false); navigate("/login"); }} className="w-full bg-spotter-600 text-white text-sm font-medium py-2 rounded-lg">Get early access</button>
          </div>
        )}
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-4 sm:px-6 pt-20 pb-16 sm:pt-32 sm:pb-24">
        <div className="flex flex-col lg:flex-row items-center gap-12">
          <div className="flex-1 text-center lg:text-left">
            <div className="inline-flex items-center gap-1.5 bg-spotter-50 text-spotter-700 text-xs font-medium px-3 py-1 rounded-full mb-5">
              <Smartphone className="w-3.5 h-3.5" />
              Built for African logistics
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 leading-tight tracking-tight">
              Fleet management<br />
              <span className="text-spotter-600">on WhatsApp</span>
            </h1>
            <p className="text-lg sm:text-xl text-gray-500 mt-4 max-w-lg mx-auto lg:mx-0">
              Track trucks, manage trips, and handle emergencies — all from WhatsApp. No hardware, no complex software.
            </p>
            <div className="flex flex-col sm:flex-row items-center gap-3 mt-8">
              <button onClick={() => navigate("/login")} className="w-full sm:w-auto flex items-center justify-center gap-2 bg-spotter-600 hover:bg-spotter-700 text-white font-medium px-6 py-2.5 rounded-lg transition">
                Start free trial <ArrowRight className="w-4 h-4" />
              </button>
              <a href="#how-it-works" className="w-full sm:w-auto text-center text-gray-600 hover:text-gray-900 font-medium px-6 py-2.5 rounded-lg border border-gray-200 hover:border-gray-300 transition">
                How it works
              </a>
            </div>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="relative w-72 sm:w-80">
              <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-4">
                <div className="flex items-center gap-2 mb-3 pb-3 border-b border-gray-100">
                  <div className="w-6 h-6 rounded-full bg-green-500" />
                  <span className="text-sm font-bold text-gray-800">WhatsApp</span>
                </div>
                <div className="space-y-3">
                  <div className="bg-spotter-50 rounded-lg p-2.5 text-xs text-gray-700 self-start max-w-[85%]">
                    *Location shared: -17.824, 31.053*<br />
                    <span className="text-gray-400 text-[10px]">Status: On Route · ETA: 2h</span>
                  </div>
                  <div className="bg-spotter-50 rounded-lg p-2.5 text-xs text-gray-700 self-start max-w-[85%]">
                    Status update: Arrived at Beitbridge border post
                  </div>
                  <div className="bg-spotter-600 text-white rounded-lg p-2.5 text-xs self-end max-w-[85%] ml-auto">
                    Trip #42: Harare → Johannesburg<br />
                    ETA 18:30. Border clearance in progress.
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-2.5 text-xs text-red-700 self-start max-w-[85%]">
                    🚨 SOS triggered — Dispatcher notified
                  </div>
                </div>
              </div>
              <div className="absolute -bottom-3 -right-3 bg-amber-400 text-amber-900 text-[10px] font-bold px-2.5 py-1 rounded-full shadow">
                WhatsApp mockup
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="bg-gray-50 py-16 sm:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-gray-900 mb-12">How it works</h2>
          <div className="grid md:grid-cols-3 gap-8">
            {[
              { step: "01", title: "Driver connects via WhatsApp", desc: "Driver messages your Trucki number. A session starts automatically — no app download." },
              { step: "02", title: "Real-time tracking & updates", desc: "Driver shares location, updates status (loading, on route, arrived), or triggers SOS — all via chat." },
              { step: "03", title: "You monitor from the dashboard", desc: "See all active trips on a live map. Get SOS alerts instantly. Manage your fleet from any browser." },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="w-12 h-12 rounded-full bg-spotter-100 text-spotter-700 font-bold text-lg flex items-center justify-center mx-auto mb-4">{item.step}</div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 max-w-xs mx-auto">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-16 sm:py-24">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <h2 className="text-2xl sm:text-3xl font-bold text-center text-gray-900 mb-4">Everything you need</h2>
          <p className="text-gray-500 text-center mb-12 max-w-lg mx-auto">No hardware, no contracts, no training. Just WhatsApp and a browser.</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f) => (
              <div key={f.title} className="bg-white border border-gray-100 rounded-xl p-5 hover:shadow-md transition">
                <div className="w-10 h-10 rounded-lg bg-spotter-50 flex items-center justify-center mb-3">
                  <f.icon className="w-5 h-5 text-spotter-600" />
                </div>
                <h3 className="font-bold text-gray-900 text-sm mb-1">{f.title}</h3>
                <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="bg-spotter-800 py-16">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 text-center">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-4">Ready to move your fleet on WhatsApp?</h2>
          <p className="text-spotter-200 mb-8 max-w-md mx-auto">Set up in 5 minutes. No hardware, no training, no commitment.</p>
          <button onClick={() => navigate("/login")} className="inline-flex items-center gap-2 bg-white text-spotter-800 font-bold px-8 py-3 rounded-lg hover:bg-spotter-50 transition">
            Start free trial <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer id="contact" className="bg-gray-900 text-gray-400 py-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-full bg-spotter-600 flex items-center justify-center">
                <Truck className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-bold text-white">Trucki</span>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <span>hello@trucki.co.zw</span>
              <span className="text-gray-600">|</span>
              <span>Zimbabwe</span>
            </div>
            <p className="text-xs">© {new Date().getFullYear()} Trucki. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
