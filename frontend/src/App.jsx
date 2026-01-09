import React, { useState } from 'react';
import DocumentViewer from './DocumentViewer';

const API_URL = "/api";

const HIGHLIGHT_STYLES = [
  { bg: "bg-red-200", border: "border-red-500" },
  { bg: "bg-orange-200", border: "border-orange-500" },
  { bg: "bg-amber-200", border: "border-amber-500" },
  { bg: "bg-yellow-200", border: "border-yellow-500" },
  { bg: "bg-lime-200", border: "border-lime-500" },
  { bg: "bg-green-200", border: "border-green-500" },
  { bg: "bg-emerald-200", border: "border-emerald-500" },
  { bg: "bg-teal-200", border: "border-teal-500" },
  { bg: "bg-cyan-200", border: "border-cyan-500" },
  { bg: "bg-sky-200", border: "border-sky-500" },
  { bg: "bg-blue-200", border: "border-blue-500" },
  { bg: "bg-indigo-200", border: "border-indigo-500" },
  { bg: "bg-violet-200", border: "border-violet-500" },
  { bg: "bg-purple-200", border: "border-purple-500" },
  { bg: "bg-fuchsia-200", border: "border-fuchsia-500" },
  { bg: "bg-pink-200", border: "border-pink-500" },
  { bg: "bg-rose-200", border: "border-rose-500" },
];

function App() {
  const [targetFile, setTargetFile] = useState(null);
  const [modFile, setModFile] = useState(null);
  const [targetText, setTargetText] = useState("");
  const [modText, setModText] = useState("");

  const [alignments, setAlignments] = useState([]);
  const [isAligning, setIsAligning] = useState(false);
  const [isAugmenting, setIsAugmenting] = useState(false);

  const [history, setHistory] = useState([]); // Stack of modText states

  const handleFileUpload = async (e, isTarget) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (isTarget) {
        setTargetFile(data.filename);
        setTargetText(data.content);
      } else {
        setModFile(data.filename);
        setModText(data.content);
        setHistory([data.content]); // Init history
      }
    } catch (err) {
      console.error(err);
      alert("Upload failed");
    }
  };

  const handleAlign = async () => {
    if (!targetText || !modText) return;
    setIsAligning(true);
    try {
      const res = await fetch(`${API_URL}/align`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_text: targetText, mod_text: modText })
      });
      const data = await res.json();
      setAlignments(data.alignments);
    } catch (err) {
      console.error(err);
      alert("Alignment failed");
    } finally {
      setIsAligning(false);
    }
  };

  const handleAugment = async () => {
    if (!targetText || !modText || alignments.length === 0) return;
    setIsAugmenting(true);
    try {
      // Push current state to history
      setHistory(prev => [...prev, modText]);

      const res = await fetch(`${API_URL}/augment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_text: targetText, mod_text: modText, alignments: alignments })
      });
      const data = await res.json();
      setModText(data.augmented_text);
    } catch (err) {
      console.error(err);
      alert("Augmentation failed");
    } finally {
      setIsAugmenting(false);
    }
  };

  const handleLoadDemo = async () => {
    try {
      const res = await fetch(`${API_URL}/demo-data`);
      const data = await res.json();

      setTargetFile(data.target.filename);
      setTargetText(data.target.content);

      setModFile(data.mod.filename);
      setModText(data.mod.content);
      setHistory([data.mod.content]);
    } catch (err) {
      console.error(err);
      alert("Failed to load demo data");
    }
  };

  const handleUndo = () => {
    if (history.length > 1) {
      const prev = history[history.length - 2]; // Get previous
      setModText(prev);
      setHistory(prevHist => prevHist.slice(0, -1)); // Pop
    }
  };

  // Prepare highlights
  const targetHighlights = alignments.map((a, i) => ({
    text: a.doc_a,
    style: HIGHLIGHT_STYLES[i % HIGHLIGHT_STYLES.length],
    topic: a.topic
  }));

  const modHighlights = alignments.map((a, i) => ({
    text: a.doc_b,
    style: HIGHLIGHT_STYLES[i % HIGHLIGHT_STYLES.length],
    topic: a.topic
  }));

  return (
    <div className="h-screen flex flex-col bg-gray-100 text-gray-900 font-sans">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex justify-between items-center shadow-sm z-10">
        <h1 className="text-xl font-bold text-indigo-600 flex items-center gap-2">
          <span className="text-2xl">⚖️</span> LegalAlign
        </h1>

        <div className="flex gap-4">
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-gray-500 uppercase mb-1">Target Document</label>
            <input type="file" onChange={(e) => handleFileUpload(e, true)} className="text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" />
          </div>
          <div className="flex flex-col">
            <label className="text-xs font-semibold text-gray-500 uppercase mb-1">Mod Document</label>
            <input type="file" onChange={(e) => handleFileUpload(e, false)} className="text-sm text-gray-600 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100" />
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleLoadDemo}
            className="px-4 py-2 rounded-lg font-medium bg-purple-600 text-white hover:bg-purple-700 shadow-sm transition-colors"
          >
            Load Demo
          </button>

          <button
            onClick={handleAlign}
            disabled={!targetText || !modText || isAligning}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${!targetText || !modText ? 'bg-gray-200 text-gray-400' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'}`}
          >
            {isAligning ? "Aligning..." : "Align Docs"}
          </button>

          <button
            onClick={handleAugment}
            disabled={alignments.length === 0 || isAugmenting}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${alignments.length === 0 ? 'bg-gray-200 text-gray-400' : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm'}`}
          >
            {isAugmenting ? "Augmenting..." : "Augment Missing"}
          </button>

          {history.length > 1 && (
            <button
              onClick={handleUndo}
              className="px-4 py-2 rounded-lg font-medium bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors"
            >
              Undo
            </button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex gap-4 p-4 overflow-hidden">
        <DocumentViewer
          title={targetFile || "Target Document"}
          text={targetText}
          highlights={targetHighlights}
        />
        <DocumentViewer
          title={modFile || "Mod Document"}
          text={modText}
          highlights={modHighlights}
        />
      </main>

      {/* Footer / Status */}
      <footer className="bg-white border-t px-6 py-2 text-xs text-gray-500 flex justify-between">
        <span>{alignments.length > 0 ? `Found ${alignments.length} aligned topics` : "Ready"}</span>
        <span>v1.0.0</span>
      </footer>
    </div>
  );
}

export default App;
