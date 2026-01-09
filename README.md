# Legal Document Alignment

This repository provides a tool to align two legal documents using GPT-5. It identifies similar topics (e.g., Definitions, Obligations, Termination) and extracts the **exact** corresponding text from each document.

## Setup

1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  Ensure you have the API key set up in `config.py` (or environment variables).

## Usage

Run the main script to align two documents:

```bash
python main.py
```

You can modify `main.py` to point to different PDF or text files.

## Features

-   **Exact Matching**: The tool ensures that the extracted text matches the original document exactly, including whitespace and punctuation.
-   **Topic Alignment**: Aligns sections based on semantic similarity (e.g., "Governing Law" in one doc matches "Choice of Law" in another).
-   **Verification**: Includes a verification step to confirm that the extracted text exists in the source documents.

## Structure

-   `main.py`: Entry point for running alignment and verification.
-   `aligner.py`: Core logic for interacting with the LLM and parsing results.
-   `utils.py`: Helper functions for reading PDF and text files.
-   `config.py`: Configuration for API keys.
# doc_align_new
