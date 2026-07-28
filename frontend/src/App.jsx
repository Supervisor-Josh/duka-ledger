import { useState } from 'react';

export default function App() {
  const [smsText, setSmsText] = useState('');
  const [ledger, setLedger] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Engine 1: Handle M-Pesa SMS Submission
  const handleSmsSubmit = async (e) => {
    e.preventDefault();
    if (!smsText.trim()) return;
    setLoading(true);
    setError('');

    try {
      const response = await fetch('http://localhost:8000/api/parse-sms', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ raw_text: smsText }),
      });

      const res = await response.json();

      if (!res || !res.data) {
        throw new Error(res?.message || 'Could not parse this SMS format');
      }

      setLedger((prev) => [res.data, ...prev]);
      setSmsText('');
    } catch (err) {
      setError(err.message || 'Error parsing transaction');
    } finally {
      setLoading(false);
    }
  };

  // Engine 2: Handle Receipt Image Scan
  const handleReceiptUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setLoading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/scan-receipt', {
        method: 'POST',
        body: formData,
      });

      const res = await response.json();

      if (res.status !== 'success') {
        throw new Error('Failed to process receipt image');
      }

      // If backend returns parsed receipt data, push to ledger, otherwise record scan event
      const scannedEntry = res.parsed_expense || {
        transaction_id: `REC-${Date.now().toString().slice(-4)}`,
        amount: 0.0,
        sender: `Receipt Image (${res.filename})`,
        type: 'EXPENSE',
        raw: `Scanned file: ${res.filename}`,
      };

      setLedger((prev) => [scannedEntry, ...prev]);
    } catch (err) {
      setError(err.message || 'Error uploading receipt');
    } finally {
      setLoading(false);
      e.target.value = ''; // Reset input selection
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 font-sans">
      <div className="max-w-2xl mx-auto bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <h1 className="text-2xl font-bold text-cyan-400 mb-1">DukaPOS</h1>
        <p className="text-xs text-slate-400 mb-6">Automated Financial Ledger Engine</p>

        {error && (
          <div className="mb-4 p-3 bg-red-900/40 border border-red-500/50 rounded text-red-300 text-sm">
            ⚠️ {error}
          </div>
        )}

        {/* ENGINE 1: SMS PARSER */}
        <form onSubmit={handleSmsSubmit} className="mb-6">
          <label className="block text-sm font-medium text-cyan-300 mb-2">
            ENGINE 1: SMS PARSER HOOK
          </label>
          <textarea
            value={smsText}
            onChange={(e) => setSmsText(e.target.value)}
            placeholder="Paste Raw M-PESA Confirmation Text..."
            className="w-full h-28 p-3 bg-slate-950 border border-slate-800 rounded-lg text-sm focus:outline-none focus:border-cyan-500 text-slate-200"
          />
          <button
            type="submit"
            disabled={loading}
            className="w-full mt-3 py-3 bg-cyan-600 hover:bg-cyan-500 font-semibold rounded-lg transition-colors text-white disabled:opacity-50"
          >
            {loading ? 'Parsing...' : 'Parse Transaction Text'}
          </button>
        </form>

        <hr className="border-slate-800 my-6" />

        {/* ENGINE 2: RECEIPT OCR UPLOADER */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-cyan-300 mb-2">
            ENGINE 2: RECEIPT IMAGE SCANNER
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleReceiptUpload}
            disabled={loading}
            className="block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-slate-800 file:text-cyan-400 hover:file:bg-slate-700 cursor-pointer disabled:opacity-50"
          />
        </div>

        {/* RECONCILED / PARSED LEDGER LIST */}
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">
            Transaction Ledger ({ledger.length})
          </h3>

          <div className="space-y-3">
            {ledger.map((item, idx) => {
              const isIncome = item.type === 'INCOME';
              return (
                <div
                  key={idx}
                  className="p-4 bg-slate-950 rounded-lg border border-slate-800 flex justify-between items-center"
                >
                  <div>
                    <p className="font-mono text-sm text-cyan-400 font-bold">
                      {item.transaction_id || item.id || 'N/A'}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      {item.sender || item.raw || 'Parsed Record'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p
                      className={`font-bold ${
                        isIncome ? 'text-emerald-400' : 'text-rose-400'
                      }`}
                    >
                      {isIncome ? '+' : '-'}Ksh {item.amount ? item.amount.toLocaleString() : '0.00'}
                    </p>
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border ${
                        isIncome
                          ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                          : 'bg-rose-950 text-rose-300 border-rose-800'
                      }`}
                    >
                      {item.type || 'EXPENSE'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}