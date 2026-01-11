import os
import random
import glob
import PyPDF2
from api.aligner_anchors import align_documents_anchors
from dotenv import load_dotenv

load_dotenv()

def extract_text_from_pdf(filepath):
    try:
        with open(filepath, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            # Limit to first 3 pages to save tokens/time for benchmark
            for page in reader.pages[:3]:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return ""

def run_benchmark():
    pdf_files = glob.glob("ndas/*.pdf")
    if len(pdf_files) < 2:
        print("Not enough PDFs in ndas/ to run benchmark.")
        return

    num_pairs = 5
    total_topics = 0
    failed_anchors = 0
    
    print(f"Running Anchor Benchmark on {num_pairs} pairs...\n")

    for i in range(num_pairs):
        # Pick two random files
        file_a = random.choice(pdf_files)
        file_b = random.choice(pdf_files)
        
        print(f"[{i+1}/{num_pairs}] Aligning: {os.path.basename(file_a)} <-> {os.path.basename(file_b)}")
        
        text_a = extract_text_from_pdf(file_a)
        text_b = extract_text_from_pdf(file_b)
        
        if not text_a or not text_b:
            print("  Skipping (empty text)")
            continue

        try:
            result = align_documents_anchors(text_a, text_b)
            
            # Check for API error string return
            if isinstance(result, str):
                print(f"  API Error: {result}")
                continue
            
            # align_documents_anchors returns a list directly, not a dict
            alignments = result 
            topics_count = len(alignments)
            total_topics += topics_count
            
            # Count failures in this batch
            batch_failures = 0
            for align in alignments:
                # Check both docs for error markers
                if "[Error:" in align.get("doc_a", "") or "[Error:" in align.get("doc_b", ""):
                    batch_failures += 1
                    
            failed_anchors += batch_failures
            
            print(f"  Topics: {topics_count}, Failures: {batch_failures}")
            
        except Exception as e:
            print(f"  Crash: {e}")

    print("\n" + "="*30)
    print("BENCHMARK RESULTS")
    print("="*30)
    if total_topics == 0:
        print("No topics found.")
    else:
        accuracy = ((total_topics - failed_anchors) / total_topics) * 100
        print(f"Total Pairs: {num_pairs}")
        print(f"Total Topics Aligned: {total_topics}")
        print(f"Failed Reconstructions: {failed_anchors}")
        print(f"Anchor Accuracy: {accuracy:.2f}%")
        print("="*30)

if __name__ == "__main__":
    run_benchmark()
