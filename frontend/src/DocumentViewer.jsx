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

            // Robust Token-Based Matching Strategy
            // 1. Exact match attempt first (fastest)
            let idx = text.indexOf(h.text);
            let length = h.text.length;

            if (idx === -1) {
                // 2. Tokenize both text and snippet to find word sequence
                // This ignores whitespace, punctuation, and weird chars
                const tokenize = (str) => {
                    const tokens = [];
                    // Match words (alphanumeric) and keep track of their indices
                    const regex = /[a-zA-Z0-9]+/g;
                    let match;
                    while ((match = regex.exec(str)) !== null) {
                        tokens.push({ word: match[0], index: match.index, end: match.index + match[0].length });
                    }
                    return tokens;
                };

                const docTokens = tokenize(text);
                const snippetTokens = tokenize(h.text);

                if (snippetTokens.length > 0) {
                    // Search for the sequence of snippet words in doc words
                    // Simple optimization: find occurrences of first word, then check rest
                    const firstWord = snippetTokens[0].word;

                    for (let i = 0; i < docTokens.length; i++) {
                        if (docTokens[i].word === firstWord) {
                            // Check potential match starting here
                            let matchFound = true;
                            if (i + snippetTokens.length > docTokens.length) {
                                matchFound = false;
                            } else {
                                for (let j = 1; j < snippetTokens.length; j++) {
                                    if (docTokens[i + j].word !== snippetTokens[j].word) {
                                        matchFound = false;
                                        break;
                                    }
                                }
                            }

                            if (matchFound) {
                                const startToken = docTokens[i];
                                const endToken = docTokens[i + snippetTokens.length - 1];
                                idx = startToken.index;
                                length = endToken.end - startToken.index;
                                break; // Stop at first match
                            }
                        }
                    }
                }
            }

            if (idx !== -1) {
                ranges.push({
                    start: idx,
                    end: idx + length,
                    style: h.style,
                    topic: h.topic
                });
            } else {
                // console.warn("STILL FAILED TO MATCH snippet");
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
