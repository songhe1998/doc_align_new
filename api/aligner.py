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

client = None # Lazy init inside functions

def align_documents(doc_a_content, doc_b_content):
    """
    Aligns two documents using GPT-5.
    """
    prompt = f"""
You are a legal document alignment expert. Your task is to align two legal documents based on similar content and topics.

Input:
=== DOCUMENT A START ===
{doc_a_content}
=== DOCUMENT A END ===

=== DOCUMENT B START ===
{doc_b_content}
=== DOCUMENT B END ===

Instructions:
1. Identify similar content or topics between the two documents (e.g., Definitions, Confidentiality Obligations, Term, Termination, Governing Law, etc.).
2. For each aligned topic, extract the EXACT text from Document A and the corresponding EXACT text from Document B.
3. The output format must be strictly:
   Topic: doc A: <text_from_A>, doc B: <text_from_B>;
   
   Example:
   Definitions: doc A: "Confidential Information" means all non-public information..., doc B: "Proprietary Information" refers to any data...;
   Obligations: doc A: Recipient agrees to hold information in strict confidence., doc B: Receiving Party shall not disclose...;

Rules:
- The text extracted must be an EXACT copy of the content in the original document, including punctuation, whitespace, and NEWLINES.
- Do NOT fix line breaks, typos, spacing errors, or PDF extraction artifacts (e.g., "discussi ons"). Copy it exactly as it appears in the input text.
- If the text is interrupted by page numbers, headers, or footers (e.g. "Page 1 of 10"), INCLUDE them in the extraction if they appear within the text block in the input.
- Do not paraphrase or summarize.
- If a topic is present in one but not the other, you can skip it or mark the missing one as "N/A".
- Separate each alignment entry with a semicolon and a newline.
- Output ONLY the alignments.
"""

    try:
        global client
        if not client:
            client = get_client()
        
        if not client:
            return "Error: OPENAI_API_KEY not configured."

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Use a valid model name (gpt-5 isn't public yet)
            messages=[
                {"role": "system", "content": "You are a precise legal assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling LLM: {e}")
        raise e # Re-raise to let the caller handle it

def parse_alignments(alignment_text):
    """
    Parses the alignment output into a structured format.
    Returns a list of dicts: [{'topic': ..., 'doc_a': ..., 'doc_b': ...}]
    """
    alignments = []
    # Split by semicolon
    items = alignment_text.split(';')
    for item in items:
        item = item.strip()
        if not item:
            continue
        
        # Expected format: Topic: doc A: ..., doc B: ...
        try:
            # Find the first colon for Topic
            first_colon = item.find(':')
            if first_colon == -1:
                continue
            
            topic = item[:first_colon].strip()
            rest = item[first_colon+1:].strip()
            
            # Find "doc A:" and "doc B:"
            # We assume "doc A:" comes first, then "doc B:"
            # But we should be robust
            
            # Simple parsing strategy: split by ", doc B:"
            # This assumes ", doc B:" is the separator. 
            # It might be risky if the text contains that string.
            # Let's try to find the indices.
            
            idx_doc_a = rest.find("doc A:")
            idx_doc_b = rest.find(", doc B:")
            
            if idx_doc_a != -1 and idx_doc_b != -1:
                content_a = rest[idx_doc_a + 6 : idx_doc_b].strip()
                content_b = rest[idx_doc_b + 8 :].strip()
                
                alignments.append({
                    'topic': topic,
                    'doc_a': content_a,
                    'doc_b': content_b
                })
        except Exception as e:
            print(f"Error parsing item '{item}': {e}")
            
    return alignments
