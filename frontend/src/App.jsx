import React, { useState } from 'react';

export default function App() {
  const [smsText, setSmsText] = useState('');
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Engine 1: Handle SMS Parsing Form Submission
  const handleSmsSubmit = async (e) => {
    e.preventDefault();
    if (!smsText.trim()) return;
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('raw_text', smsText);

      const response = await fetch('/api/parse-sms', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to parse SMS statement');
      
      const data = await response.json();
      setLedger((prev) => [data, ...prev]);
      setSmsText(''); // Clear input on success
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Engine 2: Handle Photo-to-Text Receipt Upload
  const handleReceiptUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/scan-receipt', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Failed to process receipt image');

      const data = await response.json();
      setLedger((prev) => [data, ...prev]);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="min-h-screen bg-[#0B0B0C] text-gray-100 p-4 md:p-8 font-sans">
      <div class="max-w-5xl mx-auto space-y-8">
        
        <header class="flex justify-between items-center border-b border-gray-800 pb-4">
          <div>
            <h1 class="text-2xl font-extrabold text-white tracking-tight">Duka<span class="text-emerald-500">POS</span></h1>
            <p class="text-xs text-gray-400">Automated Financial Ledger Engine</p>
          </div>
          <span class="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-xs font-mono px-3 py-1 rounded-full">
            🟢 Local Engine Connected
          </span>
        </header>

        {error && (
          <div class="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-lg text-sm">
            ⚠️ Error: {error}
          </div>
        )}

        <div class="grid md:grid-cols-2 gap-6">
          
          <div class="bg-[#161B22] border border-gray-800 p-6 rounded-xl space-y-4">
            <h2 class="text-sm font-mono text-sky-400 font-bold uppercase tracking-wider">Engine 1: SMS Parser Hook</h2>
            <form onSubmit={handleSmsSubmit} class="space-y-3">
              <label class="block text-xs text-gray-400 font-medium">Paste Raw M-PESA Confirmation Text:</label>
              <textarea
                value={smsText}
                onChange={(e) => setSmsText(e.target.value)}
                placeholder="e.g., KQA41B7G8D Confirmed. You have received Ksh2,500.00 from JOSHUA KIOKO..."
                class="w-full h-24 bg-[#0D1117] border border-gray-800 rounded-lg p-3 text-xs text-gray-300 focus:outline-none focus:border-sky-500 transition font-mono"
              />
              <button
                type="submit"
                disabled={loading}
                class="w-full bg-sky-600 hover:bg-sky-500 disabled:bg-gray-800 text-white font-semibold text-xs py-2.5 rounded-lg transition"
              >
                {loading ? 'Processing Input...' : 'Parse Transaction Text'}
              </button>
            </form>
          </div>

          <div class="bg-[#161B22] border border-gray-800 p-6 rounded-xl flex flex-col justify-between">
            <div>
              <h2 class="text-sm font-mono text-emerald-400 font-bold uppercase tracking-wider mb-4">Engine 2: Receipt OCR Vision</h2>
              <p class="text-xs text-gray-400 mb-4 leading-relaxed">
                Upload or drop a picture of a physical market receipt. The Gemini 2.5 Flash pipeline will extract the business name, items, and total amount automatically.
              </p>
            </div>
            <div class="relative border-2 border-dashed border-gray-800 rounded-lg p-6 text-center hover:border-emerald-500/40 transition">
              <input
                type="file"
                accept="image/*"
                onChange={handleReceiptUpload}
                disabled={loading}
                class="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              <div class="space-y-1 text-xs">
                <span class="text-2xl">📸</span>
                <p class="text-gray-300 font-medium">Click to select receipt image</p>
                <p class="text-gray-500 text-[11px]">Supports PNG, JPG, WebP</p>
              </div>
            </div>
          </div>

        </div>

        <div class="space-y-4">
          <h2 class="text-lg font-bold text-white tracking-tight">Unified Ledger Operations</h2>
          
          <div class="bg-[#161B22] border border-gray-800 rounded-xl overflow-hidden">
            {ledger.length === 0 ? (
              <div class="p-8 text-center text-xs text-gray-500 font-mono">
                No active statement instances registered in local memory ledger feed.
              </div>
            ) : (
              <div class="divide-y divide-gray-800">
                {ledger.map((item, idx) => (
                  <div key={idx} class="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs font-mono">
                    <div class="flex items-center space-x-3">
                      <span class={`text-lg p-2 rounded-lg ${item.flow_type === 'income' ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
                        {item.flow_type === 'income' ? '📥' : '📤'}
                      </span>
                      <div>
                        <div class="font-bold text-white text-sm">{item.party_name}</div>
                        <div class="text-[11px] text-gray-400">
                          ID: <span class="text-gray-300">{item.transaction_id}</span> &middot; Source: <span class="text-gray-300">{item.source}</span>
                        </div>
                        {item.items_detected && item.items_detected.length > 0 && (
                          <div class="mt-1 flex gap-1 flex-wrap">
                            {item.items_detected.map((tag, i) => (
                              <span key={i} class="bg-gray-800 text-gray-400 text-[10px] px-1.5 py-0.5 rounded">
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                    <div class="text-right sm:border-none border-t border-gray-800/50 pt-2 sm:pt-0">
                      <div class={`text-sm font-bold ${item.flow_type === 'income' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {item.flow_type === 'income' ? '+' : '-'} Ksh {item.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}
                      </div>
                      <div class="text-[10px] text-gray-500">{new Date(item.timestamp).toLocaleTimeString()}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
