
'use client';
import { useState, useEffect } from 'react';

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [question, setQuestion] = useState('');
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [answer, setAnswer] = useState<string>('');

  const fetchTasks = async () => {
    const res = await fetch('/api/tasks');
    const data = await res.json();
    setTasks(data);
    if (!selectedTaskId && Array.isArray(data) && data.length > 0) {
      setSelectedTaskId(data[0]?.id ?? '');
    }
  };

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    await fetch('/api/upload', {
      method: 'POST',
      body: formData,
    });
    setLoading(false);
    fetchTasks();
  };

  const handleYoutube = async () => {
    if (!youtubeUrl.trim()) return;
    setLoading(true);
    await fetch('/api/youtube', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ url: youtubeUrl.trim() }),
    });
    setLoading(false);
    setYoutubeUrl('');
    fetchTasks();
  };

  const handleAsk = async () => {
    if (!selectedTaskId || !question.trim()) return;
    setLoading(true);
    setAnswer('');
    const res = await fetch('/api/ask', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ task_id: selectedTaskId, question: question.trim(), top_k: 5 }),
    });
    const data = await res.json();
    setAnswer(data?.answer ?? JSON.stringify(data));
    setLoading(false);
  };

  const handleReprocess = async (taskId: string) => {
    setLoading(true);
    await fetch(`/api/reprocess/${taskId}`, { method: 'POST' });
    setLoading(false);
    fetchTasks();
  };

  return (
    <main className="min-h-screen bg-black text-white p-10 font-sans">
      <div className="max-w-4xl mx-auto">
        <header className="mb-12 border-b border-zinc-800 pb-6">
          <h1 className="text-4xl font-bold text-blue-500">EchoInsight v1.0</h1>
          <p className="text-zinc-400">Professional Content Digestion Engine</p>
        </header>

        <section className="bg-zinc-900 p-8 rounded-xl border border-zinc-800 mb-10">
          <h2 className="text-xl mb-4 font-semibold">Upload New Media</h2>
          <div className="flex gap-4">
            <input 
              type="file" 
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm text-zinc-400 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-zinc-800 file:text-zinc-200"
            />
            <button 
              onClick={handleUpload}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-md font-bold transition-all disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Analyze'}
            </button>
          </div>
        </section>

        <section className="bg-zinc-900 p-8 rounded-xl border border-zinc-800 mb-10">
          <h2 className="text-xl mb-4 font-semibold">YouTube Link</h2>
          <div className="flex gap-4">
            <input
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              className="block w-full rounded-md bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600"
            />
            <button
              onClick={handleYoutube}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-md font-bold transition-all disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Fetch'}
            </button>
          </div>
        </section>

        <section className="bg-zinc-900 p-8 rounded-xl border border-zinc-800 mb-10">
          <h2 className="text-xl mb-4 font-semibold">Ask (RAG)</h2>
          <div className="grid gap-3">
            <div className="flex gap-3">
              <select
                value={selectedTaskId}
                onChange={(e) => setSelectedTaskId(e.target.value)}
                className="w-full rounded-md bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm text-zinc-200"
              >
                {tasks.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.filename} — {t.status} — {t.id}
                  </option>
                ))}
              </select>
              <button
                onClick={handleAsk}
                disabled={loading}
                className="bg-emerald-600 hover:bg-emerald-700 px-6 py-2 rounded-md font-bold transition-all disabled:opacity-50"
              >
                {loading ? 'Thinking...' : 'Ask'}
              </button>
            </div>
            <input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder='z.B. "Was wurde über RAG gesagt?"'
              className="w-full rounded-md bg-zinc-950 border border-zinc-800 px-3 py-2 text-sm text-zinc-200 placeholder:text-zinc-600"
            />
            {answer && (
              <pre className="whitespace-pre-wrap text-sm text-zinc-200 bg-zinc-950 border border-zinc-800 rounded-md p-4">
                {answer}
              </pre>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-xl mb-4 font-semibold text-zinc-300">Your Insights</h2>
          <div className="grid gap-4">
            {tasks.map(task => (
              <div key={task.id} className="bg-zinc-900 p-5 rounded-lg border border-zinc-800">
                <div className="flex justify-between items-center mb-2">
                  <span className="font-mono text-xs text-zinc-500">{task.id}</span>
                  <span className={`text-xs px-2 py-1 rounded ${
                    task.status === 'COMPLETED' ? 'bg-green-900/30 text-green-400' : 'bg-yellow-900/30 text-yellow-400'
                  }`}>
                    {task.status}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <h3 className="font-bold mb-2">{task.filename}</h3>
                  <button
                    onClick={() => handleReprocess(task.id)}
                    disabled={loading}
                    className="text-xs bg-zinc-800 hover:bg-zinc-700 px-3 py-2 rounded-md font-semibold transition-all disabled:opacity-50"
                  >
                    Reprocess
                  </button>
                </div>
                {(task.summary_text || task.result_text) && (
                  <p className="text-sm text-zinc-400 leading-relaxed italic">"{task.summary_text || task.result_text}"</p>
                )}
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
