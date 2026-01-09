import React, { useState, useEffect } from 'react';

function DocumentViewer({ title, text, highlights = [], onTextChange }) {
    // Simple highlighting logic:
    // We split the text by the highlights. 
    // This is tricky if highlights overlap or are out of order.
    // For this MVP, we'll assume non-overlapping and just highlight the first occurrence of each snippet.

    const renderText = () => {
        if (!text) return <div className="text-gray-400 italic">No document loaded</div>;
        if (highlights.length === 0) return <div className="whitespace-pre-wrap">{text}</div>;

        // Sort highlights by position in text to handle them in order
        // But we don't have positions from backend, only text.
        // So we find them.

        let parts = [];
        let lastIndex = 0;

        // We need to find all occurrences and sort them.
        // But wait, if we have multiple highlights, finding them all and sorting is complex.
        // Let's try a simpler approach: 
        // We will iterate through the text and match against our list of highlight snippets.
        // Actually, let's just use a library or simple replacement for now.
        // Or just highlight the first occurrence of each unique snippet.

        // Let's map snippets to colors.
        // highlights is array of { text: "...", color: "..." }

        // We can't easily do this with simple split/join if snippets overlap or repeat.
        // Let's assume they don't overlap for now.

        // Construct a list of ranges [start, end, color]
        let ranges = [];
        highlights.forEach(h => {
            if (!h.text || h.text === "N/A") return;

            // Find all occurrences? Or just first? 
            // Let's do first for now as per plan.
            const idx = text.indexOf(h.text);
            if (idx !== -1) {
                ranges.push({ start: idx, end: idx + h.text.length, style: h.style, topic: h.topic });
            }
        });

        // Sort ranges
        ranges.sort((a, b) => a.start - b.start);

        // Filter overlaps (simple greedy)
        let nonOverlapping = [];
        let currentEnd = 0;
        ranges.forEach(r => {
            if (r.start >= currentEnd) {
                nonOverlapping.push(r);
                currentEnd = r.end;
            }
        });

        // Build JSX
        lastIndex = 0;
        nonOverlapping.forEach((r, i) => {
            // Text before
            if (r.start > lastIndex) {
                parts.push(<span key={`text-${i}`}>{text.substring(lastIndex, r.start)}</span>);
            }
            // Highlight
            parts.push(
                <span key={`high-${i}`} className={`${r.style.bg} border-b-2 ${r.style.border}`} title={r.topic}>
                    {text.substring(r.start, r.end)}
                </span>
            );
            lastIndex = r.end;
        });
        // Remaining text
        if (lastIndex < text.length) {
            parts.push(<span key="text-end">{text.substring(lastIndex)}</span>);
        }

        return <div className="whitespace-pre-wrap font-mono text-sm">{parts}</div>;
    };

    return (
        <div className="flex-1 flex flex-col h-full border rounded-lg overflow-hidden bg-white shadow-sm">
            <div className="bg-gray-50 px-4 py-2 border-b font-semibold text-gray-700 flex justify-between items-center">
                <span>{title}</span>
                <span className="text-xs text-gray-500">{text ? text.length + " chars" : ""}</span>
            </div>
            <div className="flex-1 overflow-auto p-4">
                {renderText()}
            </div>
        </div>
    );
}

export default DocumentViewer;
