import utils
import aligner
import augmenter
import os

def run_augmentation_test(file_target, file_mod):
    print(f"\n---------------------------------------------------------")
    print(f"Augmenting:\n Target: {file_target}\n Mod: {file_mod}")
    print(f"---------------------------------------------------------")
    
    content_target = utils.read_file(file_target)
    content_mod = utils.read_file(file_mod)
    
    if not content_target or not content_mod:
        print("Failed to read documents.")
        return

    print("Step 1: Aligning documents...")
    # Use standard aligner by default, but let's test anchors roughly?
    # Actually, for this test let's stick to standard alignment for simplicity unless we want to test the full new pipeline.
    # Let's switch to anchor alignment to verify compatibility.
    from api import aligner_anchors
    print("  Using Anchor Strategy for Test...")
    alignments = aligner_anchors.align_documents_anchors(content_target, content_mod)
    # print(f"Raw Alignment Output:\n{alignment_output}\n") # Anchor aligner returns object directly
    
    if not alignments or isinstance(alignments, str):
        print(f"Failed to get alignment: {alignments}")
        return
        
    # alignments = aligner.parse_alignments(alignment_output) # Not needed for anchors
    print(f"Parsed {len(alignments)} alignments.")
    
    print("Step 2: Augmenting document...")
    augmented_text = augmenter.augment_document(content_target, content_mod, alignments)
    
    output_filename = f"augmented_{os.path.basename(file_mod)}.txt"
    with open(output_filename, "w") as f:
        f.write(augmented_text)
        
    print(f"\nSaved augmented text to {output_filename}")
    
    # Verification: Check if the new text is longer
    if len(augmented_text) > len(content_mod):
        print(f"✅ Document grew in size: {len(content_mod)} -> {len(augmented_text)} chars")
    else:
        print("⚠️ Document size did not increase (might be no missing topics or failure).")

def main():
    # Test Pair: 
    # Target: 01_Bosch... (Has many standard clauses)
    # Mod: 118.3... (Short, likely missing some)
    
    target = "ndas/1588052992CCTV%20Non%20Disclosure%20Agreement.pdf"
    mod = "ndas/20150916-model-sharing-non-disclosure-agreement.pdf"
    
    run_augmentation_test(target, mod)

if __name__ == "__main__":
    main()
