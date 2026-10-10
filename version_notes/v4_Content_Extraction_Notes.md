# AI File Finder — V4 Detailed Notes

## Version 4: File Content Extraction

**Project:** AI File Finder
**Version:** V4
**Status:** Completed
**Language:** Python
**Database:** SQLite
**Search Engine:** SQLite FTS5
**API:** FastAPI
**PDF Extraction:** PyMuPDF

---

# 1. Objective of V4

The main objective of V4 was to upgrade AI File Finder from searching only file metadata to searching the actual content inside supported files.

In earlier versions, users could search for files based on filenames, paths, and file types. However, if a user remembered a sentence or keyword inside a file but did not remember its name, finding that file could be difficult.

V4 solves this by extracting text from supported files, storing the extracted text in SQLite, and indexing that content with SQLite FTS5.

### Example

Suppose a file contains:

`The Python application processes user requests and returns matching documents.`

Its filename is `project_notes.txt`.

Previously, searching for `processes user requests` might not find the file if the search examined only its filename and path.

After V4, the system can find it by searching for words in its extracted content.

**Main achievement:** The application can search inside supported files, not just their names.

---

# 2. Features Implemented in V4

1. Text extraction from `.txt` files.
2. Text extraction from `.md` files.
3. Text extraction from `.py` files.
4. Text extraction from `.dart` files.
5. Text extraction from `.js` files.
6. Text extraction from `.ts` files.
7. PDF text extraction using PyMuPDF.
8. Storage of extracted text in SQLite.
9. Full-text indexing of file content using FTS5.
10. Content-based keyword search through the CLI.
11. Content-based keyword search through FastAPI.
12. Filtering of unsupported file extensions.
13. A configurable 100,000-character extraction limit per file.
14. Database migration to add the content column without deleting existing records.
15. Updating existing indexed file records during re-indexing.

---

# 3. Technologies Used

## Python

Python is the main programming language for the project.

It coordinates folder scanning, text extraction, database operations, search logic, and API integration.

## pathlib and os

These modules help work with filesystem paths and discover files in directories.

The scanner uses folder traversal to find files and collect metadata such as filenames, paths, extensions, file sizes, and modification timestamps.

## SQLite

SQLite is the local database used to store indexed file information.

The database contains the `files` table and `search_roots` table, along with the FTS5 virtual table used for searching.

## SQLite FTS5

FTS5 is SQLite's full-text search extension.

In V4, it indexes three fields:

* `name`
* `path`
* `content`

This allows search queries to match words in extracted file content as well as filenames and paths.

## PyMuPDF

PyMuPDF is used to extract text from PDF documents.

The application opens a PDF, processes its pages, extracts their text, and returns the extracted content to the indexing process.

## FastAPI

FastAPI exposes the existing file indexing and search functionality through HTTP endpoints.

It allows other applications to search the indexed files without directly invoking the CLI.

## Uvicorn

Uvicorn runs the FastAPI application as an ASGI server.

Command:

`python -m uvicorn app.api:app --reload`

## Virtual environment

The project uses `.venv` to isolate its Python dependencies.

Packages must be installed in the same environment used to run the application.

---

# 4. Project Structure

```text
ai-file-finder/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── scanner.py
│   ├── content_extractor.py
│   └── api.py
│
├── data/
│   └── file_index.db
│
├── test-files/
│
├── requirements.txt
└── .venv/
```

### Responsibility of each file

**main.py**

* Coordinates folder indexing.
* Calls the scanner.
* Calls the text extractor.
* Inserts or updates database records.
* Removes records for files no longer found during re-indexing.
* Rebuilds the FTS5 index.
* Provides CLI functionality.

**scanner.py**

* Traverses the requested directory.
* Discovers files.
* Collects file metadata.
* Avoids following directory symlinks.
* Reports scan and error counts.

**content_extractor.py**

* Checks whether a file extension is supported.
* Extracts text from supported text-based files.
* Extracts PDF text through PyMuPDF.
* Applies the configured text-length limit.
* Returns `None` for unsupported extensions.

**database.py**

* Creates and initializes the SQLite database.
* Manages the `files` table.
* Manages the `search_roots` table.
* Creates and maintains the FTS5 virtual table.
* Performs database migrations.
* Provides database connections and search functionality.

**api.py**

* Defines FastAPI endpoints.
* Exposes file search and folder indexing.
* Connects HTTP requests to the existing application logic.

**file_index.db**

* Stores indexed file metadata.
* Stores extracted text.
* Stores registered search roots.
* Contains the FTS5 full-text search index.

---

# 5. Database Changes in V4

## Earlier database design

The `files` table already stored metadata such as:

* `id`
* `name`
* `path`
* `extension`
* `size_bytes`
* `modified_at`

V4 introduced a new column:

`content TEXT NOT NULL DEFAULT ''`

This column stores the extracted text from supported files.

## Why was the content column necessary?

Without storing extracted text, the application would need to reopen and extract every file whenever a user searched its contents.

Storing extracted text makes repeated searches faster because the application can search the indexed content instead of repeatedly reading every file from disk.

The extracted text is a stored snapshot. If a file changes, it must be re-indexed for the database content to reflect that change.

## Database migration

The migration checks whether the content column already exists before adding it.

Conceptually:

1. Read the existing table schema.
2. Check whether `content` exists.
3. If it does not exist, add the column.
4. Preserve existing records and other columns.

This approach avoids deleting the existing database simply to introduce a new field.

---

# 6. How the Content Extractor Works

The extraction logic is implemented in `app/content_extractor.py`.

## Step 1: Read the file extension

The application reads the file's suffix and converts it to lowercase.

For example:

* `notes.TXT` becomes `.txt`.
* `report.PDF` becomes `.pdf`.

This makes extension checking case-insensitive.

## Step 2: Check supported extensions

The extractor uses a set named `SUPPORTED_EXTENSIONS`.

Supported extensions:

`.txt`, `.md`, `.py`, `.dart`, `.js`, `.ts`, `.pdf`

If a file's extension is not supported, the extractor returns `None`.

The indexing process converts that `None` value into an empty string before saving the database record.

This allows the application to index the file's metadata even when it cannot extract its content.

## Step 3: Extract text from regular text files

For supported text-based files, Python opens the file in read mode using UTF-8 encoding.

The extractor uses:

`errors="replace"`

This prevents certain decoding errors from stopping extraction when the file contains invalid UTF-8 byte sequences. Some characters may be replaced when the encoding is incompatible.

The current implementation reads at most 100,000 characters per file.

## Step 4: Extract PDF text

For PDFs, PyMuPDF opens the document.

The application then:

1. Iterates through PDF pages.
2. Calls `page.get_text()` for each page.
3. Collects the extracted text.
4. Stops when the character limit has been reached.
5. Combines the extracted page text into one string.

The returned string is passed to the indexing function.

### Important limitation

PyMuPDF extracts text that exists in the PDF's text layer. A scanned document containing only images may produce little or no text. OCR is not implemented in V4.

---

# 7. The 100,000-Character Limit

V4 defines:

`MAX_EXTRACTED_CHARS = 100_000`

The extractor limits the amount of text returned for an individual file.

### Why is this useful?

* Prevents the application from storing unlimited amounts of extracted text per file.
* Helps keep the local search database manageable.
* Reduces the amount of text indexed from very large documents.
* Provides a predictable limit for the extraction stage.

### What does it not guarantee?

The limit does not restrict the original file's size.

For a regular text file, the current implementation reads only the configured number of characters. For a PDF, it processes pages until the extracted text reaches the limit, but PyMuPDF may still need to parse substantial document data.

Therefore, the character limit is a basic resource-control measure, not a complete memory or processing-time guarantee.

---

# 8. How Indexing Works in V4

The indexing process is coordinated by `index_folder()` in `app/main.py`.

## Step 1: Initialize the database

The function calls `initialize_database()`.

This ensures that the required database tables and search index are available.

## Step 2: Validate the folder

The application resolves the requested folder path and checks that it exists and is a directory.

If the path is invalid, it raises an appropriate error instead of continuing.

## Step 3: Register the search root

The folder is registered in the `search_roots` table.

This records directories that the application has been asked to index.

## Step 4: Scan the folder

The scanner discovers files and collects their metadata.

Each discovered file includes information such as its name, path, extension, size, and modification timestamp.

## Step 5: Extract content

For every discovered file, the indexing function calls:

`extract_text(file_path)`

Supported files return extracted text. Unsupported files return `None`, which is converted to an empty string before database insertion.

## Step 6: Insert or update the database record

The indexing function uses an SQL statement with:

`ON CONFLICT(path) DO UPDATE`

The `path` column is unique. When a file with the same path is already indexed, the application updates its metadata and extracted content instead of creating a duplicate record.

## Step 7: Remove missing files

After scanning, the indexing process compares the files discovered during the current scan with existing records beneath that root.

Records for files no longer found are deleted.

This cleanup occurs when the folder is re-indexed; V4 does not automatically monitor filesystem changes in real time.

## Step 8: Rebuild the FTS5 index

After updating the records, the application executes an FTS5 rebuild operation.

This synchronizes the full-text search index with the current content in the `files` table.

## Step 9: Report the result

The application prints the number of files processed.

This makes it possible to confirm that indexing completed and inspect the result from the terminal.

---

# 9. How FTS5 Searches Extracted Content

The FTS5 virtual table is configured with:

* `name`
* `path`
* `content`

It uses the `files` table as its external content source, with `id` serving as the corresponding row identifier.

Conceptually, the relationship is:

`files table → extracted content → FTS5 index → search results`

## How does searching work?

When a user submits a query:

1. The search function receives the query.
2. FTS5 matches the query against its indexed text.
3. The search function retrieves matching file records.
4. Results are returned with the relevant metadata.

Your existing `search_files()` function uses the FTS5 `MATCH` operator.

Because the FTS5 table now includes `content`, the same search mechanism can find terms within extracted text without introducing a separate content-search engine.

Your existing filename, path, prefix-search, and extension-filtering functionality remains part of the application.

## Database migration for FTS5

An existing FTS5 table created with only `name` and `path` cannot simply be assumed to include the new content column.

The migration checks the FTS5 table's columns.

If `content` is missing, the application drops and recreates the FTS5 virtual table with the new schema, then rebuilds its index.

This is a migration of the search index, not a deletion of the primary `files` table.

---

# 10. CLI Usage

Run commands from the project directory with the virtual environment active.

## Index a folder

`python -m app.main index ".\test-files"`

The application scans the directory, extracts supported file contents, stores records, and updates the search index.

## Search file content

`python -m app.main search "extraction test"`

Use a word or phrase that exists in the content of an indexed file.

## What to expect

The command should return matching files when the query matches the indexed content.

If no results are found, verify that the folder has been indexed, the word exists in the extracted text, and the search query follows the existing FTS5 query behavior.

---

# 11. FastAPI Integration

V4 retains the API built in V3 and uses the same underlying indexing and search logic.

The application can be started with:

`python -m uvicorn app.api:app --reload`

Open:

`http://127.0.0.1:8000/docs`

The interactive Swagger UI allows you to test the endpoints.

### Existing endpoints

**GET `/health`**

* Checks the application's health.

**GET `/search?q=...`**

* Searches indexed files.
* Supports the existing query parameters, including type and limit.

**POST `/index`**

* Indexes a specified folder.
* Extracts and indexes content as part of the process.

**GET `/roots`**

* Returns registered search roots.

**POST `/roots`**

* Registers a search root using the existing API implementation.

The API does not need a separate PDF extraction implementation. It uses the same `index_folder()` function and extractor as the CLI.

---

# 12. Dependency Management

V4 introduced PyMuPDF as a dependency.

Install it inside the active virtual environment:

`python -m pip install pymupdf`

Verify the import:

`python -c "import pymupdf; print('PyMuPDF installed successfully')"`

If the FastAPI server is also needed, ensure FastAPI and Uvicorn are installed in the same environment.

To record the installed dependencies:

`python -m pip freeze > requirements.txt`

### Environment lesson

A package installed in the system Python environment is not automatically available in the project's `.venv`.

Use the project's interpreter to install dependencies and run the API:

`python -m pip install ...`

`python -m uvicorn app.api:app --reload`

This helps avoid environment mismatches.

---

# 13. Testing and Verification

The following behaviors should be checked before declaring V4 complete.

## Extraction tests

* TXT and Markdown content can be extracted.
* Supported source-code files can be extracted.
* PDF text can be extracted using PyMuPDF.
* Unsupported extensions return `None`.
* Text extraction respects the configured character limit.
* Unusual text encodings do not cause a decoding failure.

## Database tests

* The `files` table contains the `content` column.
* The FTS5 table includes `name`, `path`, and `content`.
* Re-indexing updates existing records.
* The index is rebuilt after indexing.
* Missing files are removed from the indexed records when the folder is re-indexed.

## CLI tests

* Folder indexing completes successfully.
* Extracted content is stored.
* A query matching only the file content can find the file.
* Existing filename and extension searches still work.

## API tests

* Uvicorn starts successfully from the project environment.
* The Swagger UI opens.
* Search returns matching files.
* The indexing endpoint extracts and indexes content.
* Content searches work through the API.

### Recorded outcome

During V4 development, the user verified successful indexing of test files, confirmed that extracted content existed in SQLite, confirmed that the FTS5 schema included `name`, `path`, and `content`, and tested content searches through both the CLI and API.

The PDF extraction changes and subsequent API environment issue were resolved, and the user confirmed that the application was working through both interfaces.

---

# 14. Limitations of V4

V4 provides content-based keyword search, but it does not yet understand semantic meaning.

### Keyword matching

The search engine depends on words indexed by FTS5. Queries using completely different wording may fail to find conceptually related documents.

### Supported formats

Only the explicitly supported extensions are extracted. Word documents, spreadsheets, images, ZIP files, and other formats are not supported by the V4 extractor.

### Scanned PDFs

PDFs containing image-only scanned pages may require OCR.

### Content updates

A file changed on disk is not automatically re-indexed. The user must run indexing again.

### Large files

The character limit reduces the amount of extracted text per file but does not provide a complete processing-time or memory limit.

### Ranking

FTS5 provides keyword-based relevance ranking, but that ranking is not a semantic similarity score.

These limitations provide the motivation for the next versions.

---

# 15. What I Learned in V4

1. How to extract text from different file types using Python.
2. How to use PyMuPDF to extract PDF text.
3. How to store extracted content in SQLite.
4. How SQLite FTS5 indexes and searches text.
5. How to extend an existing database schema without deleting existing records.
6. How to update existing indexed records with SQL conflict handling.
7. How to integrate extraction into an existing indexing pipeline.
8. How to expose the same functionality through a REST API and CLI.
9. How to manage Python dependencies inside a virtual environment.
10. How to consider resource limits and extraction errors when working with real files.

---

# 16. Interview Explanation

In V4 of my AI File Finder project, I implemented file content extraction so users could search inside supported documents rather than only search filenames and paths.

I used Python for the extraction pipeline, PyMuPDF for PDF text extraction, SQLite to store the extracted content, and SQLite FTS5 to index and search that content.

I extended the existing database schema with a content column and updated the indexing process to extract, insert, update, and re-index file contents. I also retained the existing CLI and FastAPI integration, so content search works through both interfaces.

This version provides the foundation for semantic search, which I plan to implement in V5 using text embeddings and vector similarity.

---

# 17. V4 Final Summary

**V4's main achievement:** AI File Finder can search the contents of supported files.

The main pipeline is:

`Folder → Scanner → Content Extractor → SQLite → FTS5 Index → Search Results`

The application now combines file metadata search with full-text content search while preserving the existing database and API architecture.

**Next version: V5 — Semantic Search**

V5 will introduce text embeddings so the system can retrieve conceptually related files even when the query does not use exactly the same words as the file content.

The planned progression is:

* V4: Search by words inside files.
* V5: Search by semantic similarity.
* V6: Combine keyword and semantic search through hybrid search.
