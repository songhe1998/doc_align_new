import utils

file_b = "ndas/Mutual-Non-Disclosure-Agreement-EN.pdf"
content = utils.read_file(file_b)
print(f"Content length: {len(content)}")

# Search for the substring "3.1 In the context"
start_idx = content.find("3.1 In the context")
if start_idx != -1:
    print(f"Found at {start_idx}")
    print(f"Context: '{content[start_idx:start_idx+100]}'")
else:
    print("Substring '3.1 In the context' not found.")
    # Try fuzzy search or just print a chunk
    print("Printing first 2000 chars:")
    print(content[:2000])
