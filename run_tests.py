import utils
import aligner
import os

def run_test(file_a, file_b):
    print(f"\n---------------------------------------------------------")
    print(f"Testing Pair:\n A: {file_a}\n B: {file_b}")
    print(f"---------------------------------------------------------")
    
    content_a = utils.read_file(file_a)
    content_b = utils.read_file(file_b)
    
    if not content_a or not content_b:
        print("Failed to read documents.")
        return False

    print("Aligning documents...")
    alignment_output = aligner.align_documents(content_a, content_b)
    
    if not alignment_output:
        print("Failed to get alignment from LLM.")
        return False
        
    alignments = aligner.parse_alignments(alignment_output)
    print(f"Parsed {len(alignments)} alignments.")
    
    print("Verifying alignments...")
    # We use the verify_alignment function from main.py logic, but let's reimplement/copy it here or import it if we refactored.
    # Since main.py has it, let's just copy the logic for simplicity or import main if possible.
    # I'll just copy the logic to be safe and independent.
    
    valid = True
    for align in alignments:
        topic = align['topic']
        text_a = align['doc_a']
        text_b = align['doc_b']
        
        # Check A
        if text_a != "N/A":
            if text_a not in content_a:
                print(f"❌ Mismatch in Doc A for topic '{topic}'")
                print(f"   Expected: ...{text_a[:50]}...")
                valid = False

        # Check B
        if text_b != "N/A":
            if text_b not in content_b:
                print(f"❌ Mismatch in Doc B for topic '{topic}'")
                print(f"   Expected: ...{text_b[:50]}...")
                valid = False
                
    if valid:
        print("✅ Alignment Verified Successfully!")
    else:
        print("⚠️ Alignment Verification Failed.")
        
    return valid

def main():
    test_pairs = [
        (
            "ndas/Agency-Lending-Disclosure_A-Z-Guide_Appendix_Sample-Confidentiality-Agreements.pdf",
            "ndas/Annex 18 - Non-Disclosure Agreement.pdf"
        ),
        (
            "ndas/Confidentiality_and_Non-Disclosure_Agreement.pdf",
            "ndas/Mutual-Non-Disclosure-Agreement-EN.pdf"
        ),
        (
            "ndas/Non-Disclosure-Agreement-NDA.pdf",
            "ndas/Startup_Pack_nondisclosure_agreement.pdf"
        ),
        (
            "ndas/Non-Disclosure-Agreement_12.pdf",
            "ndas/Non-Disclosure-Agreement_3.pdf"
        ),
        (
            "ndas/Mutual-Non-Disclosure-Agreement-Inventor-Product-Development-Experts-Inc..pdf",
            "ndas/Mutual_Nondisclosure_Agreement.pdf"
        )
    ]
    
    results = []
    for f_a, f_b in test_pairs:
        if os.path.exists(f_a) and os.path.exists(f_b):
            success = run_test(f_a, f_b)
            results.append((f_a, f_b, success))
        else:
            print(f"Skipping pair {f_a} vs {f_b} (file not found)")
            
    print("\n\n================ SUMMARY ================")
    for f_a, f_b, success in results:
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {os.path.basename(f_a)} vs {os.path.basename(f_b)}")

if __name__ == "__main__":
    main()
