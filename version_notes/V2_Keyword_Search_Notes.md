# AI File Finder — V2: Better Keyword Search

## 1. Goal of V2

The goal of V2 was to improve the basic keyword search from V1.

V1 could find files using simple `LIKE` queries, but it had limited relevance ranking and search capabilities.

V2 introduced:

* Relevance-based search
* File-type filtering
* SQLite FTS5
* BM25 ranking
* Prefix search
* Better search-index handling

The main idea was:

```text
V1:
Query → SQLite LIKE → Results

V2:
Query → FTS5 → Relevance Ranking → Filters → Results
```

---

# 2. Relevance Ranking

### Problem in V1

The original search used:

```sql
WHERE name LIKE ?
   OR path LIKE ?
ORDER BY name
```

This could find matching files, but it didn't understand which result was more relevant.

For example, when searching for:

```text
project
```

these could all match:

```text
project.dart
project_notes.txt
my_project.dart
documents/project/readme.txt
```

Alphabetical ordering does not necessarily mean relevance.

### What we implemented

We initially added a relevance score using SQL `CASE`:

```sql
CASE
    WHEN name = ? THEN 4
    WHEN name LIKE ? THEN 3
    WHEN name LIKE ? THEN 2
    WHEN path LIKE ? THEN 1
    ELSE 0
END AS relevance
```

The idea was:

```text
Exact filename match       → highest
Filename starts with query → high
Filename contains query    → medium
Path contains query        → lower
```

This introduced the important search-engine concept of **ranking results instead of simply finding matches**.

Later, after introducing FTS5, ranking was handled by:

```sql
bm25(file_search)
```

---

# 3. SQLite FTS5

## What is FTS?

FTS means **Full-Text Search**.

Instead of repeatedly doing:

```sql
LIKE '%project%'
```

we created an SQLite FTS5 search index.

The database now has:

```text
files
│
├── id
├── name
├── path
├── extension
├── size_bytes
└── modified_at

file_search
│
├── name
└── path
```

The `files` table remains the source of truth.

The `file_search` table is used specifically for text searching.

---

# 4. External-Content FTS Table

We created:

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS file_search
USING fts5(
    name,
    path,
    content='files',
    content_rowid='id'
)
```

Two important concepts:

### `content='files'`

The actual file data remains in the `files` table.

### `content_rowid='id'`

The FTS index connects its records to:

```text
files.id
```

This allows us to search using FTS and then retrieve the complete file metadata from `files`.

The flow is:

```text
User query
    ↓
file_search
    ↓
matching rowid
    ↓
files.id
    ↓
complete file metadata
```

---

# 5. FTS Synchronization

Creating an external-content FTS table does not automatically populate it with existing records.

Therefore, after indexing files, we rebuild the FTS index:

```sql
INSERT INTO file_search(file_search)
VALUES ('rebuild')
```

Our indexing flow became:

```text
Scan filesystem
      ↓
Insert / update files table
      ↓
Remove stale files
      ↓
Rebuild FTS index
```

We intentionally chose rebuilding for V2 because it keeps the implementation simple.

We did NOT introduce:

* SQLite triggers
* background indexing
* incremental FTS synchronization
* complicated indexing queues

Those can be considered later if the project actually needs them.

---

# 6. BM25 Relevance Ranking

We replaced our simple ranking with SQLite's:

```sql
bm25(file_search)
```

BM25 is a common information-retrieval ranking algorithm.

It gives each matching result a relevance score.

Our query uses:

```sql
ORDER BY relevance
```

With SQLite's BM25 implementation, **smaller values represent better matches**, so we order ascending.

The important concept is not memorizing the formula.

The important concept is:

```text
Search
   ↓
Find candidate documents
   ↓
Calculate relevance
   ↓
Rank results
   ↓
Return best results
```

This is an important foundation for later semantic and hybrid search.

---

# 7. File-Type Filtering

We added an optional file extension filter.

Example:

```powershell
python -m app.main search project --type .dart
```

This means:

```text
Search query = project
Extension = .dart
```

The SQL adds:

```sql
AND files.extension = ?
```

The extension comes from the scanner:

```python
file_path.suffix.lower()
```

Examples:

```text
.dart
.py
.txt
.md
.js
.ts
```

This gives users a simple way to narrow search results.

---

# 8. Prefix Search

Normal FTS searches complete tokens.

For example:

```text
flutt
```

does not automatically mean:

```text
flutter
```

We added prefix searching by converting a simple single-word query:

```text
flutt
```

into:

```text
flutt*
```

The FTS engine can then find words beginning with that prefix.

Examples:

```text
flutt  → flutter
proj   → project
doc    → documents
```

We intentionally kept this simple.

We did not build a custom search-query parser.

---

# 9. Current Search Flow

Our V2 search flow is now approximately:

```text
User
  │
  │  search project --type .dart
  ▼
main.py
  │
  ▼
search_folder()
  │
  ▼
search_files()
  │
  ├── build FTS query
  ├── apply optional extension filter
  │
  ▼
SQLite FTS5
  │
  ├── MATCH
  ├── BM25 relevance
  │
  ▼
files table
  │
  ▼
Ranked results
  │
  ▼
CLI output
```

---

# 10. Problems We Intentionally Did NOT Solve Yet

V2 is not supposed to be a complete search engine.

We intentionally postponed:

* Fuzzy search
* Typo correction
* Semantic search
* Embeddings
* Vector databases
* File-content search
* Natural-language queries
* AI-generated answers
* Live filesystem monitoring
* Background indexing
* Distributed search
* Advanced query parsing

These belong to later versions.

---

# 11. What I Learned From V2

The most important concepts learned in V2 are:

### Search is not just matching

Finding results and ranking results are different problems.

```text
Retrieval → Which files match?
Ranking   → Which matching files are most relevant?
```

### Keyword search and semantic search are different

```text
Keyword search:
"flutter"
     ↓
Find text containing/matching flutter

Semantic search:
"files related to Flutter development"
     ↓
Find files based on meaning
```

We'll eventually use both.

### Search indexes exist for a reason

Instead of repeatedly scanning raw data:

```text
Filesystem → Search every file
```

we build an index:

```text
Filesystem
    ↓
Index
    ↓
Fast retrieval
```

This same general idea appears in databases, search engines, and vector search systems.

---

# 12. V2 Final Stack

```text
Python
   │
   ├── pathlib / os
   │
   ├── SQLite
   │     ├── files table
   │     ├── search_roots table
   │     └── FTS5 index
   │
   └── CLI / argparse
```

V2 does **not use AI yet**.

That is intentional.

We are building the deterministic search foundation first.

---

# V2 Completion Status

| Feature               | Status   |
| --------------------- | -------- |
| Relevance ranking     | ✅        |
| File-type filtering   | ✅        |
| SQLite FTS5           | ✅        |
| BM25 ranking          | ✅        |
| Prefix search         | ✅        |
| Multiple search roots | ✅        |
| Stale-file cleanup    | ✅        |
| Re-indexing           | ✅        |
| Semantic search       | ⏭️ Later |
| AI/RAG                | ⏭️ Later |

## Key takeaway

The project has now evolved from:

```text
V1
"Scan files and search the database"
```

to:

```text
V2
"Maintain a searchable file index and retrieve                    
relevant files efficiently using full-text search."        
```

That is a solid foundation for the next stage.         
