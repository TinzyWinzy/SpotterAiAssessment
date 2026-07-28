import { useState } from "react";
import { AlertTriangle, X, Loader2 } from "lucide-react";

interface Props {
  onConfirm: (message: string) => Promise<void>;
  onDismiss: () => void;
}

export function SOSAlert({ onConfirm, onDismiss }: Props) {
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);

  async function handleSend() {
    setSending(true);
    try {
      await onConfirm(message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 flex items-end sm:items-center justify-center p-4">
      <div className="bg-white rounded-2xl w-full max-w-sm shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="bg-red-600 px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-white">
            <AlertTriangle className="w-5 h-5" />
            <span className="font-bold text-base">SOS Alert</span>
          </div>
          <button onClick={onDismiss} className="text-white/80 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="px-5 py-4 space-y-4">
          <p className="text-sm text-gray-700">
            This will notify your dispatcher with your current location and trip details. An SOS alert requires immediate attention.
          </p>

          <div>
            <label className="text-xs text-gray-500 font-medium block mb-1">
              Additional message (optional)
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="e.g. Breakdown at border, need assistance..."
              rows={3}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-transparent resize-none"
            />
          </div>

          <button
            onClick={handleSend}
            disabled={sending}
            className="w-full py-3 bg-red-600 text-white rounded-lg font-bold text-sm hover:bg-red-700 active:bg-red-800 disabled:opacity-50 transition-colors min-h-[48px] flex items-center justify-center"
          >
            {sending ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              "Send SOS Alert"
            )}
          </button>

          <button
            onClick={onDismiss}
            disabled={sending}
            className="w-full py-2 text-sm text-gray-500 font-medium hover:text-gray-700"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
