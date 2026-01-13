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

  const [useAnchors, setUseAnchors] = useState(false); // Experimental Toggle
  const [augmentHighlights, setAugmentHighlights] = useState([]); // Store inserted clauses for highlighting

  // Helper to handle fetch errors
  const fetchWithCheck = async (url, options) => {
    // Standard REST call (Render does not strip paths)
    const res = await fetch(url, options);
    // ... (rest of fetchWithCheck)
    if (!res.ok) {
      const text = await res.text();
      let errorMsg = `Server Error ${res.status}`;
      try {
        const json = JSON.parse(text);
        if (json.detail) errorMsg += `: ${json.detail}`;
        else errorMsg += `: ${text}`;
      } catch (e) {
        errorMsg += `: ${text.substring(0, 200)}`; // Truncate HTML
      }
      throw new Error(errorMsg);
    }
    return res.json();
  };

  const handleFileUpload = async (event, isTarget) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const data = await fetchWithCheck(`${API_URL}/upload`, {
        method: "POST",
        body: formData,
      });

      if (isTarget) {
        setTargetFile(data.filename);
        setTargetText(data.content);
      } else {
        setModFile(data.filename);
        setModText(data.content);
        setHistory((prev) => [...prev, data.content]);
      }
    } catch (err) {
      console.error(err);
      alert(err.message);
    }
  };

  // State for interactive highlighting
  const [selectedTopics, setSelectedTopics] = useState(new Set());

  // ... (handleAlign stays same, but we need to reset selection on new align)
  // modifying setAlignments in handleAlign to also clear selection
  // Actually, better to do it in a useEffect or just set it in handleAlign

  const handleAlign = async () => {
    if (!targetText || !modText) return;
    setIsAligning(true);
    setAlignments([]);
    setSelectedTopics(new Set()); // Reset selection
    try {
      const data = await fetchWithCheck(`${API_URL}/align`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_text: targetText,
          mod_text: modText,
          strategy: useAnchors ? "anchors" : "standard"
        })
      });
      setAlignments(data.alignments);
      // Optional: If we wanted to select all by default:
      // setSelectedTopics(new Set(data.alignments.map((_, i) => i)));
    } catch (err) {
      console.error(err);
      alert(err.message);
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

      const data = await fetchWithCheck(`${API_URL}/augment`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_text: targetText, mod_text: modText, alignments: alignments, strategy: useAnchors ? "anchors" : "standard" })
      });
      setModText(data.augmented_text);

      // Handle Augmentation Highlights
      if (data.insertions) {
        const newHighlights = data.insertions.map(ins => ({
          text: ins.text,
          style: { bg: "bg-green-100", border: "border-green-500" },
          topic: "Augmented: " + ins.topic
        }));
        setAugmentHighlights(newHighlights);
      }
    } catch (err) {
      console.error(err);
      alert(err.message);
    } finally {
      setIsAugmenting(false);
    }
  };

  const handleLoadDemo = async () => {
    try {
      const data = await fetchWithCheck(`${API_URL}/demo-data`);

      setTargetFile(data.target.filename);
      setTargetText(data.target.content);

      setModFile(data.mod.filename);
      setModText(data.mod.content);
      setHistory([data.mod.content]);
    } catch (err) {
      console.error(err);
      alert(err.message);
    }
  };

  const handleUndo = () => {
    if (history.length > 1) {
      const prev = history[history.length - 2]; // Get previous
      setModText(prev);
      setHistory(prevHist => prevHist.slice(0, -1)); // Pop
    }
  };

  // handleFileUpload was implemented above, wait, check if it was lost.
  // The previous read showed line 120 was collapsing everything.
  // I need to make sure I don't duplicate handleFileUpload if it was defined *before* the collapsed block.
  // Looking at file history, handleFileUpload was defined *before* handleAlign in previous versions, but my last edit replaced handleAlign AND collapsed others.
  // Let's assume handleFileUpload is NOT in the collapsed block if I put it *before*. 
  // Wait, in Step 1652 I put handleFileUpload *before* handleAlign.
  // In Step 1752 I replaced handleAlign and put the collapsed comment *after* handleAlign.
  // So handleAugment, handleLoadDemo, handleUndo correspond to the comment.
  // handleFileUpload is likely safe *above* handleAlign.
  // Wait, Step 1752 snippet shows:
  // ... handleAlign implementation ...
  // headers ...
  // ... setAlignments ...
  // ... setIsAligning(false) ...
  // };
  // 
  // // ... (handleAugment, handleLoadDemo, handleUndo, handleFileUpload stay same)
  //
  // So the comment REPLACED handleAugment, handleLoadDemo, handleUndo.
  // It effectively deleted them.
  // So I must restore them.

  // Toggle selection
  const toggleTopic = (index) => {
    const newSet = new Set(selectedTopics);
    if (newSet.has(index)) {
      newSet.delete(index);
    } else {
      newSet.add(index);
    }
    setSelectedTopics(newSet);
  };

  // Prepare highlights - FILTERED by selection
  const targetHighlights = alignments
    .map((a, i) => ({ ...a, originalIndex: i }))
    .filter((a) => selectedTopics.has(a.originalIndex))
    .map((a) => ({
      text: a.doc_a,
      style: HIGHLIGHT_STYLES[a.originalIndex % HIGHLIGHT_STYLES.length],
      topic: a.topic
    }));

  const modHighlights = alignments
    .map((a, i) => ({ ...a, originalIndex: i }))
    .filter((a) => selectedTopics.has(a.originalIndex))
    .map((a) => ({
      text: a.doc_b,
      style: HIGHLIGHT_STYLES[a.originalIndex % HIGHLIGHT_STYLES.length],
      topic: a.topic
    }))
    .concat(augmentHighlights); // Merge augmented highlights

  return (
    <div className="h-screen flex flex-col bg-gray-100 text-gray-900 font-sans">
      {/* Header (Keep as is, just collapsed for brevity in tool call) */}
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
          {/* Buttons... */}
          <button onClick={handleLoadDemo} className="px-4 py-2 rounded-lg font-medium bg-purple-600 text-white hover:bg-purple-700 shadow-sm transition-colors">Load Demo</button>

          <div className="flex items-center gap-2 bg-gray-50 px-3 py-2 rounded-lg border">
            <input
              type="checkbox"
              id="anchorToggle"
              checked={useAnchors}
              onChange={(e) => setUseAnchors(e.target.checked)}
              className="w-4 h-4 text-indigo-600"
            />
            <label htmlFor="anchorToggle" className="text-xs font-semibold text-gray-600 cursor-pointer select-none">
              Exp. Mode (Anchors)
            </label>
          </div>

          <button onClick={handleAlign} disabled={!targetText || !modText || isAligning} className={`px-4 py-2 rounded-lg font-medium transition-colors ${!targetText || !modText ? 'bg-gray-200 text-gray-400' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'}`}>
            {isAligning ? "Aligning..." : "Align Docs"}
          </button>
          <button onClick={handleAugment} disabled={alignments.length === 0 || isAugmenting} className={`px-4 py-2 rounded-lg font-medium transition-colors ${alignments.length === 0 ? 'bg-gray-200 text-gray-400' : 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-sm'}`}>
            {isAugmenting ? "Augmenting..." : "Augment Missing"}
          </button>
          {history.length > 1 && (
            <button onClick={handleUndo} className="px-4 py-2 rounded-lg font-medium bg-gray-200 text-gray-700 hover:bg-gray-300 transition-colors">Undo</button>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex gap-4 p-4 overflow-hidden relative">
        {/* Document Viewers */}
        <div className="flex-1 flex gap-4 overflow-hidden">
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
        </div>

        {/* Legend Sidebar - Interactive Checklist */}
        {alignments.length > 0 && (
          <div className="w-80 bg-white border rounded-lg shadow-sm flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b bg-gray-50 font-semibold text-gray-700 text-sm flex justify-between items-center">
              <span>Aligned Topics</span>
              <span className="text-xs font-normal text-gray-500">{selectedTopics.size} / {alignments.length} selected</span>
            </div>
            <div className="flex-1 overflow-auto p-2 space-y-2">
              {alignments.map((a, i) => {
                const style = HIGHLIGHT_STYLES[i % HIGHLIGHT_STYLES.length];
                const isSelected = selectedTopics.has(i);

                // Determine Status
                const hasA = a.doc_a && a.doc_a !== "N/A" && !a.doc_a.includes("[Error:");
                const hasB = a.doc_b && a.doc_b !== "N/A" && !a.doc_b.includes("[Error:");

                let badge = null;
                if (hasA && hasB) badge = <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-green-100 text-green-700">BOTH</span>;
                else if (hasA) badge = <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">LEFT ONLY</span>;
                else if (hasB) badge = <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-orange-700">RIGHT ONLY</span>;
                else badge = <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">N/A</span>;

                return (
                  <div
                    key={i}
                    onClick={() => toggleTopic(i)}
                    className={`flex items-center gap-3 p-3 rounded-md border text-sm cursor-pointer transition-all ${isSelected ? `${style.bg} ${style.border} border-l-4` : 'bg-white border-gray-200 hover:bg-gray-50'}`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => { }} // We handle click on parent div
                      className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 pointer-events-none"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center mb-1">
                        <span className="font-semibold text-gray-800 truncate">{a.topic}</span>
                        {badge}
                      </div>
                      {isSelected && (
                        <div className="text-xs text-gray-600 truncate opacity-75">
                          {hasA ? "Left: " + a.doc_a.substring(0, 30) + "..." : "Left: N/A"}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>

      {/* Footer / Status */}
      <footer className="bg-white border-t px-6 py-2 text-xs text-gray-500 flex justify-between">
        <span>{alignments.length > 0 ? `Found ${alignments.length} aligned topics` : "Ready"}</span>
        <span>v2.2-Checklist</span>
      </footer>
    </div>
  );
}

export default App;
