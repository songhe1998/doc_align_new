import utils
import aligner

file_a = "ndas/Mutual-Non-Disclosure-Agreement-Inventor-Product-Development-Experts-Inc..pdf"
file_b = "ndas/Mutual_Nondisclosure_Agreement.pdf"

content_a = utils.read_file(file_a)
content_b = utils.read_file(file_b)

print("Aligning...")
alignment_output = aligner.align_documents(content_a, content_b)
print(f"Raw Output: {alignment_output}")
alignments = aligner.parse_alignments(alignment_output)

for align in alignments:
    print(f"Topic found: {align['topic']}")
    if True: # Check all topics
        text_a = align['doc_a']
        print(f"LLM Output A (repr): {repr(text_a)}")
        
        # Find this roughly in content_a
        start_snippet = text_a[:20]
        idx = content_a.find(start_snippet)
        if idx != -1:
            actual_in_file = content_a[idx:idx+len(text_a)]
            print(f"File Content A (repr): {repr(actual_in_file)}")
            
            if text_a == actual_in_file:
                print("MATCH A!")
            else:
                print("MISMATCH A!")
                # Find first difference
                for i, (c1, c2) in enumerate(zip(text_a, actual_in_file)):
                    if c1 != c2:
                        print(f"Difference at index {i}: LLM='{repr(c1)}', File='{repr(c2)}'")
                        break
        else:
            print("Could not find start of snippet in file A.")
