# AI File Finder — V3: FastAPI Backend

## 1. Overview

### Goal of V3

The goal of V3 was to expose the existing AI File Finder functionality through a REST API.

In V1, the application scanned local files and stored their metadata in SQLite.

In V2, the application introduced better keyword search using SQLite FTS5, BM25 ranking, prefix search, and file-type filtering.

In V3, we added FastAPI so external clients can communicate with the existing Python application through HTTP requests and JSON responses.

The main transformation was:

```text
V1: Scan files and store metadata

V2: Search indexed files efficiently

V3: Expose indexing and search through a REST API
```

V3 still does not use AI. It establishes the backend foundation for future versions and a future Flutter Desktop client.

---

## 2. Technology Stack

| Technology  | Purpose                                       |
| ----------- | --------------------------------------------- |
| Python      | Main programming language                     |
| FastAPI     | Creates REST API endpoints                    |
| Uvicorn     | Runs the API server                           |
| Pydantic    | Validates request data                        |
| SQLite      | Stores indexed file metadata and search roots |
| SQLite FTS5 | Performs full-text keyword search             |
| BM25        | Ranks search results                          |
| pathlib     | Resolves and validates filesystem paths       |
| argparse    | Preserves the existing CLI interface          |

### Dependencies

Installed the required API packages:

```powershell
python -m pip install fastapi "uvicorn[standard]"
```

Saved the installed dependencies:

```powershell
python -m pip freeze > requirements.txt
```

`requirements.txt` allows the environment's installed packages to be recorded for future setup. Since `pip freeze` records the entire active environment, review the file if you later want to maintain a smaller, curated dependency list.

---

## 3. Project Structure

The project gained a new API entry point.

```text
ai-file-finder/
│
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── database.py
│   ├── scanner.py
│   └── api.py
│
├── data/
│   └── file_index.db
│
├── test-files/
├── requirements.txt
└── .venv/
```

### Responsibilities of each file

**`main.py`**

Contains the original CLI interface, including indexing and search commands. Its `index_folder()` function is reused by the API.

**`scanner.py`**

Scans folders recursively and collects file metadata, including name, path, extension, size, and modification time.

**`database.py`**

Manages SQLite connections, search roots, file records, and FTS5 search functionality.

**`api.py`**

Defines the FastAPI application and exposes HTTP endpoints.

**`file_index.db`**

Stores the application's persistent index.

The important design decision is that `api.py` acts as an interface to the existing application logic rather than implementing a second scanner or search engine.

---

## 4. What Is a REST API?

REST API stands for Representational State Transfer Application Programming Interface.

In this project, it allows another program to request file-search or indexing operations from our Python backend.

For example:

```text
GET /search?q=flutter
```

The client sends an HTTP request, FastAPI calls the Python search function, and the server returns the results as JSON.

The general flow is:

```text
Client
  |
  | HTTP request
  v
FastAPI endpoint
  |
  v
Existing Python function
  |
  v
SQLite / Filesystem
  |
  v
Python result
  |
  v
JSON response
```

A REST API separates how a client communicates with the application from how the application performs its internal work.

This is useful because the same backend can later serve a Flutter Desktop application without rewriting the search logic.

---

## 5. Creating the FastAPI Application

The application was created in `app/api.py`.

```python
from fastapi import FastAPI

app = FastAPI(
    title="AI File Finder API",
    description="API for searching and indexing local files.",
    version="3.0.0",
)
```

### Important concepts

**`FastAPI(...)`**

Creates the application instance.

**`app`**

The FastAPI application object used to register endpoints and run the server.

**`title`, `description`, and `version`**

Provide API metadata displayed in the interactive documentation.

### The health endpoint

```python
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
    }
```

This endpoint confirms that the API is responding.

A successful response looks like:

```json
{
  "status": "healthy",
  "version": "3.0.0"
}
```

The health endpoint is a basic availability check; it does not independently prove that every database operation or indexing feature is working.

---

## 6. Running the API Server

The development server is started using:

```powershell
python -m uvicorn app.api:app --reload
```

### Understanding the command

* `python -m uvicorn` runs Uvicorn through the active Python environment.
* `app.api` refers to the `api.py` module inside the `app` package.
* `:app` identifies the FastAPI instance inside that module.
* `--reload` automatically restarts the development server when code changes.

The local server is available at:

```text
http://127.0.0.1:8000
```

### Interactive documentation

```text
http://127.0.0.1:8000/docs
```

FastAPI generates interactive API documentation from the registered endpoints and their parameter definitions.

This makes it possible to test requests without writing a separate frontend.

---

## 7. Database Initialization with Lifespan

Initially, database initialization was called inside individual endpoints.

We then moved initialization to FastAPI's application lifespan.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield
```

The application is configured to use the lifespan function:

```python
app = FastAPI(
    title="AI File Finder API",
    description="API for searching and indexing local files.",
    version="3.0.0",
    lifespan=lifespan,
)
```

### How lifespan works

```text
FastAPI starts
      |
      v
initialize_database()
      |
      v
yield
      |
      v
API handles requests
      |
      v
Application shuts down
```

The code before `yield` runs during startup. The code after `yield`, if added, runs during shutdown.

This means the database tables are initialized when the application starts, rather than being initialized repeatedly by the search and roots-listing endpoints.

The existing `index_folder()` function is left unchanged because it also supports the original CLI workflow.

---

## 8. GET /health

### Purpose

Checks whether the API is responding.

### Request

```http
GET /health
```

Full URL:

```text
http://127.0.0.1:8000/health
```

### Example response

```json
{
  "status": "healthy",
  "version": "3.0.0"
}
```

### Learning outcome

Understood how to define a GET endpoint and return a JSON response.

---

## 9. GET /search

### Purpose

Searches files that have already been indexed.

The endpoint reuses the existing `search_files()` function from `database.py`.

### Supported query parameters

| Parameter | Meaning                   | Example   |
| --------- | ------------------------- | --------- |
| `q`       | Search query              | `flutter` |
| `type`    | Optional file extension   | `.dart`   |
| `limit`   | Maximum number of results | `5`       |

The `q` parameter is required. The extension is optional, and the result limit defaults to 20, with a maximum of 100.

### Example 1: Search by keyword

```http
GET /search?q=flutter
```

URL:

```text
http://127.0.0.1:8000/search?q=flutter
```

### Example 2: Filter by file type

```http
GET /search?q=flutter&type=.dart
```

This returns matching indexed files with the `.dart` extension.

### Example 3: Limit results

```http
GET /search?q=flutter&limit=5
```

This returns at most five matching results.

### Example 4: Combine parameters

```http
GET /search?q=flutter&type=.dart&limit=5
```

This combines keyword search, extension filtering, and result limiting.

### Search implementation

The endpoint calls the existing search function:

```python
results = search_files(
    q.strip(),
    limit,
    type,
)
```

The results are converted into JSON-friendly dictionaries:

```python
return {
    "query": q,
    "count": len(results),
    "results": [dict(row) for row in results],
}
```

### Example response

```json
{
  "query": "flutter",
  "count": 1,
  "results": [
    {
      "id": 2,
      "name": "flutter_notes.txt",
      "path": "D:\\gen-ai\\ai-file-finder\\test-files\\flutter_notes.txt",
      "extension": ".txt",
      "size_bytes": 256,
      "modified_at": 1791510000.0,
      "relevance": -0.000001
    }
  ]
}
```

This is an illustrative response. Actual records, counts, metadata, and relevance scores depend on the indexed files.

### Important detail

The search endpoint searches indexed file names and paths. It does not search the contents of the files yet.

---

## 10. GET /roots

### Purpose

Returns the list of registered search roots.

A search root is a directory registered in the `search_roots` table.

### Request

```http
GET /roots
```

### Implementation

```python
@app.get("/roots")
def list_roots():
    roots = get_search_roots()

    return {
        "count": len(roots),
        "roots": [
            {
                "id": root["id"],
                "path": root["path"],
            }
            for root in roots
        ],
    }
```

The exact implementation also uses the database initialization performed during application startup.

### Example response

```json
{
  "count": 1,
  "roots": [
    {
      "id": 1,
      "path": "D:\\gen-ai\\ai-file-finder\\test-files"
    }
  ]
}
```

### Learning outcome

Learned how to retrieve records from SQLite and return them as a structured JSON response.

---

## 11. POST /roots

### Purpose

Registers a directory as a search root.

This operation adds a root to the database. It does not automatically scan the folder.

### Request body

```json
{
  "path": "D:\\gen-ai\\ai-file-finder\\test-files"
}
```

### Pydantic request model

```python
from pydantic import BaseModel


class RootRequest(BaseModel):
    path: str
```

Pydantic validates the shape and type of the incoming request body. Here, the request must contain a string field named `path`.

### Endpoint logic

The endpoint:

1. Resolves the submitted path.
2. Checks whether it exists.
3. Checks whether it is a directory.
4. Registers the directory through `add_search_root()`.
5. Returns a JSON response.

Conceptually:

```text
JSON request
     |
     v
RootRequest validation
     |
     v
Resolve folder path
     |
     v
Check existence and directory type
     |
     v
add_search_root()
     |
     v
JSON response
```

### Example success response

```json
{
  "status": "success",
  "path": "D:\\gen-ai\\ai-file-finder\\test-files",
  "message": "Search root registered successfully"
}
```

### Duplicate root handling

The existing database function uses `INSERT OR IGNORE` and a unique constraint on the root path.

Registering the same resolved path twice therefore does not create a duplicate database record.

### Invalid path handling

The endpoint returns HTTP 400 for a nonexistent folder or a path that points to a file rather than a directory.

### Important distinction

Registering a root and indexing it are separate operations.

* `POST /roots` registers the directory.
* `POST /index` scans the directory and updates the file index.

---

## 12. POST /index

### Purpose

Indexes a folder through the REST API.

The endpoint reuses the existing `index_folder()` function in `main.py`.

### Request body

```json
{
  "folder": "D:\\gen-ai\\ai-file-finder\\test-files"
}
```

### Pydantic model

```python
class IndexRequest(BaseModel):
    folder: str
```

### Endpoint flow

```text
POST /index
      |
      v
Validate JSON body
      |
      v
Resolve the folder path
      |
      v
index_folder()
      |
      v
Recursive filesystem scan
      |
      v
Insert / update file records
      |
      v
Remove stale records
      |
      v
Rebuild FTS5 index
      |
      v
Return JSON response
```

### Example response

```json
{
  "status": "success",
  "folder": "D:\\gen-ai\\ai-file-finder\\test-files",
  "message": "Folder indexed successfully"
}
```

The actual indexing work is handled by the existing indexing function, including its file processing and search-index maintenance.

### Why reuse `index_folder()`?

We avoid duplicating the indexing logic in `api.py`.

This ensures the CLI and API can use the same scanner and database behavior.

---

## 13. Query Parameters vs Request Bodies

V3 introduced two important ways to send information to an API.

### Query parameters

Used by the search endpoint:

```text
/search?q=flutter&type=.dart&limit=5
```

They are part of the URL and are suitable for search terms and optional filters.

### JSON request bodies

Used by the root registration and indexing endpoints:

```json
{
  "path": "D:\\some-folder"
}
```

or:

```json
{
  "folder": "D:\\some-folder"
}
```

The request body is useful for structured input to operations such as registering and indexing directories.

---

## 14. Input Validation

FastAPI uses type annotations and `Query(...)` to validate search parameters.

The search endpoint supports constraints equivalent to:

```python
q: str = Query(min_length=1)

type: str | None = Query(default=None)

limit: int = Query(
    default=20,
    ge=1,
    le=100,
)
```

### What these constraints mean

* `min_length=1`: the query must contain at least one character.
* `default=None`: the extension filter is optional.
* `ge=1`: the limit must be at least one.
* `le=100`: the limit cannot exceed 100.

FastAPI automatically returns a validation error when these constraints are violated.

Pydantic models also validate the structure and data types of JSON request bodies.

Note that validation of the request's shape does not replace application-level checks such as confirming that a directory actually exists.

---

## 15. Error Handling

The project added controlled errors for invalid directory paths and invalid search syntax.

### HTTP 400 — Bad Request

Used for invalid client input, such as a nonexistent directory or malformed search syntax detected by SQLite.

Example:

```json
{
  "detail": "Folder does not exist: D:\\missing-folder"
}
```

### HTTP 422 — Validation Error

FastAPI typically returns HTTP 422 when the request does not meet declared validation rules.

Examples include:

* Missing the required `q` parameter.
* Supplying a limit outside the permitted range.
* Omitting a required JSON field.

### Handling SQLite FTS5 errors

The search endpoint catches `sqlite3.OperationalError` and returns a controlled error response instead of exposing the raw database error to the client.

This is a useful starting point, but `OperationalError` can also indicate problems unrelated to query syntax. A production implementation should distinguish malformed search input from genuine database failures.

### Important limitation

Not every unexpected failure is automatically converted into HTTP 400. The application should not classify every database error as the client's fault. Unexpected server failures should be logged and handled separately.

---

## 16. Complete API Endpoint Reference

| Method | Endpoint  | Purpose                   |
| ------ | --------- | ------------------------- |
| GET    | `/health` | Check API availability    |
| GET    | `/search` | Search indexed files      |
| POST   | `/index`  | Index or refresh a folder |
| GET    | `/roots`  | List registered roots     |
| POST   | `/roots`  | Register a search root    |

The endpoints are available through the local development server:

```text
http://127.0.0.1:8000
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 17. How V3 Fits into the Existing Architecture

The architecture now has two interfaces that reuse the same underlying Python logic.

```text
                 User
                  |
          +-------+-------+
          |               |
          v               v
      CLI / V1-V2      REST API / V3
          |               |
          |               v
          |            FastAPI
          |               |
          +-------+-------+
                  |
                  v
         Existing Python logic
          |               |
          v               v
      scanner.py      database.py
                          |
                          v
                  SQLite + FTS5
```

The API does not replace the CLI. Both remain useful for different tasks.

The CLI is useful for local development and direct operations. The API provides a standard interface for future client applications.

---

## 18. Testing Completed in V3

The following features were implemented and tested during development:

* [x] FastAPI application starts successfully.
* [x] Health endpoint returns JSON.
* [x] Search works through HTTP.
* [x] Search supports filename and keyword queries.
* [x] File-type filtering works.
* [x] Result limits work.
* [x] Folder indexing works through the API.
* [x] Search roots can be listed.
* [x] Search roots can be registered.
* [x] Duplicate root registration does not create duplicates.
* [x] Invalid folder paths are rejected.
* [x] Database initialization moved to the application lifespan.
* [x] Invalid FTS query handling was added.
* [x] Existing CLI functionality remains part of the project.

These are development-stage checks. Before calling the backend production-ready, additional tests should cover unexpected database errors, malformed request bodies, empty or whitespace-only queries, concurrent requests, and filesystem permission failures.

---

## 19. What Was Intentionally Postponed?

V3 focuses on exposing the existing system through an API.

The following features were not added:

* Authentication and authorization
* Public deployment
* Docker
* Redis
* Background task queues
* Async database access
* Concurrent or parallel indexing
* Semantic search and embeddings
* Vector databases
* RAG
* AI agents
* Flutter Desktop UI
* File-content extraction

These are not requirements for a useful first API. They can be introduced when a later version needs them.

### Local security consideration

The API can access files available to the Python process. It should remain bound to `127.0.0.1` during local development. Before exposing it to a network or connecting untrusted clients, add suitable access controls and restrict which folders can be indexed.

---

## 20. What I Learned from V3

### 1. How a REST API works

A client sends an HTTP request, the server executes application logic, and the server returns a response.

### 2. How to create API endpoints

Used FastAPI decorators such as:

```python
@app.get("/search")
@app.post("/index")
```

### 3. How to work with JSON

Returned dictionaries and lists as JSON responses and accepted structured JSON request bodies.

### 4. How Pydantic helps validate input

Created request models such as `RootRequest` and `IndexRequest`.

### 5. How to reuse existing application logic

The API delegates indexing and searching to existing functions instead of creating duplicate implementations.

### 6. How to initialize resources during application startup

Used FastAPI lifespan to initialize the database once per application startup.

### 7. How to handle client errors

Used HTTP status codes and controlled error messages for invalid input.

### 8. How an API enables frontend integration

A future Flutter application can send requests and receive JSON instead of accessing SQLite or implementing file indexing itself.

---

## 21. What Comes Next — V4

V4 will introduce **file-content extraction**.

Currently, the system searches file names and paths. It cannot search for words that exist only inside a document.

For example, if a file named `meeting_notes.txt` contains the phrase `project deadline`, V2/V3 cannot find it using that phrase unless it appears in the filename or path.

V4 will introduce a content-extraction pipeline:

```text
Indexed file
     |
     v
Detect file type
     |
     v
Extract readable text
     |
     v
Store extracted content
     |
     v
Search file content
```

Potential supported formats include:

* `.txt`
* `.md`
* `.py`
* `.dart`
* `.js`
* `.ts`
* PDF, with an appropriate text-extraction library

We should start with straightforward text formats before adding PDFs or more complicated file types.

This step will provide the foundation for later semantic search and retrieval-augmented generation.

---

## Final Takeaway

V3 transformed AI File Finder from a command-line-only application into a Python backend accessible through a REST API.

The project now supports:

* Local file indexing
* SQLite FTS5 keyword search
* BM25 relevance ranking
* Search filtering and result limits
* Search-root management
* HTTP requests and JSON responses
* Automatic database initialization at API startup

The key engineering lesson is that a well-designed API can expose existing application logic without rewriting it.

**V1 built the index. V2 improved retrieval. V3 made the system accessible to other applications.**
