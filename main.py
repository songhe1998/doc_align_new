import os
import utils
import aligner

def normalize_text(text):
    """
    Normalizes text for comparison (removes extra whitespace).
    """
    return " ".join(text.split())

def verify_alignment(alignments, doc_a_content, doc_b_content):
    """
    Verifies that the aligned text exists in the original documents.
    """
    valid = True
    
    # Normalize original docs for easier matching (optional, but PDF extraction can be messy)
    # However, the user asked for EXACT match. 
    # If the LLM output is slightly different due to PDF extraction artifacts, we might need to be careful.
    # Let's try strict check first.
    
    for align in alignments:
        topic = align['topic']
        text_a = align['doc_a']
        text_b = align['doc_b']
        
        # Check A
        if text_a != "N/A":
            if text_a not in doc_a_content:
                print(f"❌ Mismatch in Doc A for topic '{topic}'")
                print(f"   Expected: ...{text_a[:50]}...")
                print(f"   Status: Not found in document.")
                valid = False
            else:
                print(f"✅ Doc A match for '{topic}'")

        # Check B
        if text_b != "N/A":
            if text_b not in doc_b_content:
                print(f"❌ Mismatch in Doc B for topic '{topic}'")
                print(f"   Expected: ...{text_b[:50]}...")
                print(f"   Status: Not found in document.")
                valid = False
            else:
                print(f"✅ Doc B match for '{topic}'")
                
    return valid

def main():
    # Define test files
    file_a = "ndas/1588052992CCTV%20Non%20Disclosure%20Agreement.pdf"
    file_b = "ndas/20150916-model-sharing-non-disclosure-agreement.pdf"
    
    print(f"Reading {file_a}...")
    content_a = utils.read_file(file_a)
    print(f"Reading {file_b}...")
    content_b = utils.read_file(file_b)
    
    if not content_a or not content_b:
        print("Failed to read documents.")
        return

    print("Aligning documents...")
    alignment_output = aligner.align_documents(content_a, content_b)
    
    if not alignment_output:
        print("Failed to get alignment from LLM.")
        return
        
    print("\n=== Raw Output ===")
    print(alignment_output)
    print("==================\n")
    
    alignments = aligner.parse_alignments(alignment_output)
    print(f"Parsed {len(alignments)} alignments.")
    
    print("\nVerifying alignments...")
    is_perfect = verify_alignment(alignments, content_a, content_b)
    
    if is_perfect:
        print("\n🎉 Alignment is PERFECT!")
    else:
        print("\n⚠️ Alignment has issues.")

if __name__ == "__main__":
    main()
