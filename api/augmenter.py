from openai import OpenAI
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

def identify_missing_topics(alignments):
    """
    Identifies topics that are present in Doc A (Target) but missing in Doc B (Mod).
    Returns a list of dicts: [{'topic': ..., 'target_content': ...}]
    """
    missing = []
    for align in alignments:
        # Check if Doc B is N/A or empty
        if align['doc_b'] == "N/A" or not align['doc_b'].strip():
            # Ensure Doc A has content
            if align['doc_a'] != "N/A" and align['doc_a'].strip():
                missing.append({
                    'topic': align['topic'],
                    'target_content': align['doc_a']
                })
    return missing

def generate_missing_clause(target_clause, mod_full_text, topic):
    """
    Generates a new clause for the missing topic, matching the style of the mod document.
    """
    # Take a sample of the mod document to understand style
    style_sample = mod_full_text[:2000] + "\n...\n" + mod_full_text[-1000:]
    
    prompt = f"""
You are a legal expert and skilled legal drafter.
Your task is to draft a new legal clause for a specific topic, to be inserted into an existing document ("Mod Document").

Target Clause (Source of Truth):
"{target_clause}"

Mod Document Style Sample:
=== START SAMPLE ===
{style_sample}
=== END SAMPLE ===

Instructions:
1. Read the "Target Clause" to understand the legal obligation/definition required.
2. Read the "Mod Document Style Sample" to understand the tone, terminology (e.g., "Company" vs "Discloser", "Shall" vs "Will"), and formatting.
3. Draft a NEW clause that covers the same legal ground as the Target Clause but is written EXACTLY in the style of the Mod Document.
4. Do not include any introductory text. Output ONLY the new clause.
"""

    try:
        global client
        if not client:
            client = get_client()
            
        if not client:
            return None

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a precise legal drafter."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating clause: {e}")
        return None

def determine_insertion_point(mod_full_text, new_clause, topic):
    """
    Determines the best insertion point for the new clause.
    Returns the index in mod_full_text where the clause should be inserted, 
    and potentially a prefix/suffix (like newlines).
    """
    # We will ask the LLM to identify the preceding text snippet.
    
    prompt = f"""
You are a legal document editor.
We need to insert a new clause about "{topic}" into the following document.

New Clause:
"{new_clause}"

Document:
=== START DOCUMENT ===
{mod_full_text}
=== END DOCUMENT ===

Instructions:
1. Analyze the structure of the document.
2. Find the most logical place to insert the new clause. It should be grouped with similar topics or placed in a standard order (e.g., Definitions first, General Provisions last).
3. Identify the exact text snippet (approx 20-50 chars) that should IMMEDIATELY PRECEDE the new clause.
4. Output the result in this format:
   PRECEDING_SNIPPET: <exact text from document>
   
   Example:
   PRECEDING_SNIPPET: Section 3. Confidentiality.
"""

    try:
        global client
        if not client:
            client = get_client()
        
        if not client:
             return len(mod_full_text), "\n\n"
             
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        content = response.choices[0].message.content
        
        if "PRECEDING_SNIPPET:" in content:
            snippet = content.split("PRECEDING_SNIPPET:")[1].strip()
            # Remove quotes if the LLM added them
            if snippet.startswith('"') and snippet.endswith('"'):
                snippet = snippet[1:-1]
            
            # 1. Try Exact Search
            idx = mod_full_text.find(snippet)
            if idx != -1:
                return idx + len(snippet), "\n\n"
            
            # 2. Try Fuzzy Search
            try:
                from fuzzysearch import find_near_matches
                # Allow some errors relative to snippet length
                max_dist = min(5, int(len(snippet) * 0.2)) 
                matches = find_near_matches(snippet, mod_full_text, max_l_dist=max_dist)
                
                if matches:
                    print(f"DEBUG: Found insertion point via fuzzy match: {matches[0]}")
                    return matches[0].end, "\n\n"
            except ImportError:
                 print("Warning: fuzzysearch not installed, skipping fuzzy insertion.")
                 
            # 3. Fallback: Split snippet?
            # If still nothing, warn and append
            print(f"Could not find snippet '{snippet}' in text (Exact or Fuzzy).")
                
    except Exception as e:
        print(f"Error determining insertion point: {e}")

    # Fallback: Append to end
    return len(mod_full_text), "\n\n"

def augment_document(target_text, mod_text, alignments):
    """
    Main function to augment the mod document.
    """
    missing_items = identify_missing_topics(alignments)
    print(f"Found {len(missing_items)} missing topics.")
    
    augmented_text = mod_text
    
    # Sort insertions by index to avoid messing up offsets? 
    # Actually, if we insert one by one, we need to be careful.
    # Easiest is to do it one by one and re-calculate indices or just do it.
    # But determine_insertion_point uses the full text. 
    # If we modify text, the next insertion point might be wrong if we use the original text.
    # Let's update the text iteratively.
    
    # Track insertions for frontend highlighting
    insertions = []
    
    for item in missing_items:
        topic = item['topic']
        target_content = item['target_content']
        
        print(f"Processing missing topic: {topic}")
        
        # 1. Generate Clause
        new_clause = generate_missing_clause(target_content, mod_text, topic) # Use original mod text for style sample
        if not new_clause:
            print("Failed to generate clause.")
            continue
            
        print(f"Generated clause: {new_clause[:50]}...")
        
        # 2. Determine Insertion Point (in the CURRENT augmented_text)
        idx, prefix = determine_insertion_point(augmented_text, new_clause, topic)
        
        # 3. Insert
        # We might need a suffix too, usually newlines
        suffix = "\n"
        
        insertion = prefix + new_clause + suffix
        augmented_text = augmented_text[:idx] + insertion + augmented_text[idx:]
        
        # Record insertion for frontend
        insertions.append({
            "topic": topic,
            "text": new_clause # backend returns just the clause text for fuzzy matching
        })
        
    return {
        "augmented_text": augmented_text,
        "insertions": insertions
    }
