from openai import OpenAI
import re

try:
    import config
except ImportError:
    from . import config

def get_client():
    api_key = config.OPENAI_API_KEY
    if not api_key:
        print("Warning: OPENAI_API_KEY is not set.")
        return None
    return OpenAI(api_key=api_key)

client = None

def align_documents_anchors(doc_a_content, doc_b_content):
    """
    Aligns documents by asking LLM for start/end anchors (first 2 words, last 2 words).
    Then reconstructs the full text by finding these anchors in the source.
    """
    prompt = f"""
You are a precise legal document alignment assistant.
Your goal is to identify similar topics in two documents.

Input:
=== DOC A ===
{doc_a_content}
=== END DOC A ===

=== DOC B ===
{doc_b_content}
=== END DOC B ===

Task:
1. Find similar topics (e.g. Definitions, Term, Termination).
2. For each topic, do NOT output the full text. Instead, output the FIRST 2 WORDS and LAST 2 WORDS of the relevant clause for that topic.
3. Format:
   Topic: <TopicName>;
   DocA_Start: <first 2 words>, DocA_End: <last 2 words>;
   DocB_Start: <first 2 words>, DocB_End: <last 2 words>;
   
   Example:
   Topic: Confidentiality;
   DocA_Start: The Recipient, DocA_End: strict confidence.;
   DocB_Start: Receiving Party, DocB_End: not disclose.;
   
Rules:
- Be extremely precise with the anchors. They must match the document exactly.
- If a topic is missing in one doc, write "N/A" for start/end.
- Output ONLY the structured data.
"""

    try:
        global client
        if not client:
            client = get_client()
        
        if not client:
            return "Error: OPENAI_API_KEY not set"

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a robotic alignment tool."},
                {"role": "user", "content": prompt}
            ]
        )
        
        raw_output = response.choices[0].message.content
        print("DEBUG: Anchor Output:", raw_output)
        
        return parse_and_reconstruct(raw_output, doc_a_content, doc_b_content)

    except Exception as e:
        import traceback
        print(f"Error in anchor aligner: {e}")
        # print(traceback.format_exc()) # Optional: print stack trace
        # Return error string to be caught by index.py
        return f"Error in anchor aligner: {str(e)}"

def reconstruct_text(full_text, start_anchor, end_anchor):
    if start_anchor == "N/A" or end_anchor == "N/A":
        return "N/A"

    # --- Strategy 1: Exact Match (Fastest) ---
    start_idx = full_text.find(start_anchor)
    end_idx = -1
    
    if start_idx != -1:
        end_idx = full_text.find(end_anchor, start_idx)

    # --- Strategy 2: Regex Whitespace Match (Handles \n vs space) ---
    if start_idx == -1:
        try:
            # Escape symbols, allow 1+ whitespace chars for every space
            start_pattern = re.escape(start_anchor).replace(r'\ ', r'\s+')
            match = re.search(start_pattern, full_text)
            if match:
                start_idx = match.start()
        except:
            pass

    if start_idx != -1 and end_idx == -1:
        try:
            end_pattern = re.escape(end_anchor).replace(r'\ ', r'\s+')
            # Search for end anchor starting from start_idx
            match = re.search(end_pattern, full_text[start_idx:])
            if match:
                end_idx = start_idx + match.start()
        except:
            pass
            
    # --- Strategy 3: Fuzzy Match (Handles typos/OCR errors) ---
    try:
        from fuzzysearch import find_near_matches
        
        # Helper for fuzzy search
        def fuzzy_find(query, text, start_from=0, max_l_dist=2):
            matches = find_near_matches(query, text[start_from:], max_l_dist=max_l_dist)
            if matches:
                 # Return absolute index of best match (first one usually best in fuzzysearch)
                 return start_from + matches[0].start
            return -1

        if start_idx == -1:
            start_idx = fuzzy_find(start_anchor, full_text)
            
        if start_idx != -1 and end_idx == -1:
             end_idx = fuzzy_find(end_anchor, full_text, start_from=start_idx)

    except ImportError:
        print("Warning: fuzzysearch not installed, skipping fuzzy step.")

    # --- Strategy 4: Fallback (First/Last Word) ---
    if start_idx == -1:
        # Try finding just the first word
        first_word = start_anchor.split()[0]
        start_idx = full_text.find(first_word)
    
    if start_idx == -1:
        return f"[Error: Start anchor '{start_anchor}' not found]"
        
    if end_idx == -1:
        # Try finding just the last word, searching AFTER start_idx
        last_word = end_anchor.split()[-1]
        end_idx = full_text.find(last_word, start_idx)
    
    if end_idx == -1:
         return f"[Error: End anchor '{end_anchor}' not found after start]"
         
    # Extract including the end anchor length
    # Note: If fuzzy match, typical length of anchor is len(end_anchor) roughly.
    return full_text[start_idx : end_idx + len(end_anchor)]

def parse_and_reconstruct(output, doc_a, doc_b):
    alignments = []
    
    # Robust Regex Pattern
    # Looks for Topic: ... ; DocA_Start: ... , DocA_End: ... ; DocB_Start: ... , DocB_End: ... ;
    # Handles optional whitespace, newlines, and potential bolding (**Topic**)
    
    # We'll split by "Topic:" to find blocks first, or just iterate through matches if we can define a full block pattern.
    # Given the complexity, let's try to find all blocks that look like a topic definition.
    
    # Pattern to capture groups: Topic, A_Start, A_End, B_Start, B_End
    # We use non-greedy matches (.*?) and allow for multiline (re.DOTALL not strictly needed if we structure right)
    
    pattern = r"Topic:\s*(?P<topic>.*?)[;\n]" \
              r".*?DocA_Start:\s*(?P<a_start>.*?),\s*(?:DocA_End|End):\s*(?P<a_end>.*?)[;\n]" \
              r".*?DocB_Start:\s*(?P<b_start>.*?),\s*(?:DocB_End|DocA_End|End):\s*(?P<b_end>.*?)[;\n]"
              
    matches = re.finditer(pattern, output, re.IGNORECASE | re.DOTALL)
    
    for match in matches:
        try:
            topic = match.group("topic").strip()
            a_start = match.group("a_start").strip()
            a_end = match.group("a_end").strip()
            b_start = match.group("b_start").strip()
            b_end = match.group("b_end").strip()
            
            # Additional cleanup if LLM leaves quotes
            def clean(s): return s.strip('"').strip("'")
            a_start = clean(a_start)
            a_end = clean(a_end)
            b_start = clean(b_start)
            b_end = clean(b_end)
            
            # Reconstruct
            text_a = reconstruct_text(doc_a, a_start, a_end)
            text_b = reconstruct_text(doc_b, b_start, b_end)
            
            alignments.append({
                "topic": topic,
                "doc_a": text_a,
                "doc_b": text_b,
                "strategy": "anchors"
            })
        except Exception as e:
             print(f"Error processing match: {e}")

    # Fallback: If regex fails completely, return the raw output as a special single topic for debugging
    if not alignments:
        print("DEBUG: Parsing failed. Raw output snippet:", output[:100])
        # Return a dummy error alignment so the user sees something happened
        alignments.append({
            "topic": "DEBUG: Parsing Failed",
            "doc_a": f"Could not parse LLM output.\nRaw:\n{output}",
            "doc_b": "Check logs.",
            "style": {"bg": "bg-red-200", "border": "border-red-400"} # Manual style override? App.jsx handles styles dynamically.
        })
            
    return alignments
