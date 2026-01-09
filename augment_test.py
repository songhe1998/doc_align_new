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
    alignment_output = aligner.align_documents(content_target, content_mod)
    print(f"Raw Alignment Output:\n{alignment_output}\n")
    
    if not alignment_output:
        print("Failed to get alignment.")
        return
        
    alignments = aligner.parse_alignments(alignment_output)
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
