# Astra File System

This document explains how the file system works in `astra-poc-vc`, what kinds of files are supported, which operations are available, and how the agent and UI use the file layer.

## Overview

The Astra file system is a sandboxed document workspace used by the agent, the frontend file explorer, and the backend API.

At a high level, it provides:

- A safe root directory for user files
- File and folder listing
- Search by topic, file type, and timeframe
- Open and preview flows for Markdown, PDFs, and images
- Structured document creation for Markdown and PDF outputs
- Markdown and PDF merge flows, including logical synthesis for Markdown and cover-page merge for PDFs
- File management operations such as rename, move, delete, and folder creation
- File organization by type, extension, filename meaning, alphabetical bucket, and semantic meaning/domain

The implementation lives primarily in:

- [tools_files.py](/Users/scr/Projects/astra/PoC/astra-poc-vc/tools_files.py)
- [main.py](/Users/scr/Projects/astra/PoC/astra-poc-vc/main.py)
- [AIOSFileExplorer.tsx](/Users/scr/Projects/astra/PoC/astra-poc-vc/tauri-app/src/components/aios/AIOSFileExplorer.tsx)

## File Root And Sandbox

Files are resolved inside a sandboxed base directory. The default location is:

```text
data/personas/mike/files
```

This can be overridden with the `PERSONA_FILES_DIR` environment variable.

The backend protects the sandbox using safe path resolution. Any path that tries to escape the base directory is rejected. That means operations like listing, opening, moving, renaming, and deleting are constrained to Astra's file space.

## Supported File Types

The current supported extensions are:

### Markdown files

- `.md`

### PDF files

- `.pdf`

### Image files

- `.png`
- `.jpg`
- `.jpeg`
- `.gif`
- `.webp`
- `.bmp`
- `.svg`

These are grouped into broad categories:

- `documents`
- `images`
- `other`

## What The File System Can Do

The file system is more than simple storage. It behaves like a lightweight content layer for the agent.

### 1. List files and folders

The system can return:

- Files in the root or a subdirectory
- Folder inventory for the current directory
- Counts for files and folders
- Breadcrumbs for navigation
- Filters used in the request

Each file record includes useful metadata such as:

- `filename`
- `path`
- `type`
- `category`
- `size_label`
- `modified_at`
- `domains`
- `preview`
- `thumbnail`
- `raw_url`

### 2. Search files semantically

Search uses lightweight metadata from:

- Filename
- Preview text
- Summary points
- Tags
- Domains

This makes queries like these possible:

- "pricing files"
- "recent documents"
- "files from yesterday"
- "travel notes"

The search layer also understands some time-related wording such as:

- `today`
- `yesterday`
- `recent`
- `latest`
- `last week`
- `this week`
- `last month`

### 3. Preview and open files

The backend builds a viewer payload for a file. Depending on the file type, the UI can present it as:

- Text preview
- PDF
- Image

The backend now runs a cached ingestion pass for supported files. Markdown files are read directly into text mode, PDFs attempt text extraction for the same text-mode summary path, and images are placed into image-analysis mode with cached metadata.

### 4. Create Markdown and PDF documents

The file layer can create new documents directly through the agent tool surface.

There are two creation tools:

- `create_markdown_document`
- `create_pdf_document`

Both tools are designed for structured composition rather than raw text dumping.
They accept:

- A document title
- An optional introduction
- An ordered list of sections
- An optional destination folder
- An optional filename override

Each section can include:

- `heading`
- `body`
- `bullets`
- optional source hints such as a topic-like heading or matching file reference

When section bodies are omitted, the system can infer content from matching existing document files and synthesize concise section text from cached ingestion output instead of copying the source file verbatim.

### 5. Merge Markdown and PDF files

The file layer can also combine existing files into a new output document.

There are two merge tools:

- `merge_markdown_files`
- `merge_pdf_files`

The behaviors are intentionally different:

- Markdown merge is logical:
  - Creates a new Markdown document
  - Adds a title and introduction
  - Lists source files
  - Builds one synthesized section per source file using ingestion summaries and key points
  - Avoids pasting the full raw body when a summary-style merge is possible
- PDF merge is physical plus structured:
  - Creates a new PDF
  - Adds a generated cover page first
  - Lists included source PDFs and merge order
  - Preserves the original PDF pages after the cover page

This distinction matters:

- Use `create_markdown_document` or `create_pdf_document` when the user wants a coherent new document
- Use `merge_markdown_files` when the user wants a combined Markdown brief
- Use `merge_pdf_files` when the user wants several PDFs packaged into one PDF while keeping original pages

### 6. Create folders

New folders can be created inside the sandbox, either:

- At the root
- Inside an existing subdirectory

### 7. Rename files

Files can be renamed safely within their current directory.

### 8. Move files

Astra supports several move patterns:

- Move one file to another folder
- Move multiple files in one operation
- Move all supported files from one folder into another folder

When name collisions happen, Astra automatically appends a numeric suffix instead of overwriting the destination file.

### 9. Categorize and separate files

Astra can now organize files into folders automatically through the agent tool layer.

Supported grouping strategies:

- `type` → `Documents`, `Images`, `Other`
- `extension` → folders like `PDF`, `PNG`, `MD`
- `name` → folders based on the first meaningful filename token like `Acme` or `Helsinki`
- `alphabetical` → `A`, `B`, `C`, `0-9`, `Other`
- `meaning` → semantic buckets derived from the domain router like `Sales`, `Travel`, `Finance`, `Admin`

The categorization flow:

- Resolves files inside the sandbox
- Computes the bucket name from the selected strategy
- Creates destination folders as needed
- Moves files safely with name deduping
- Supports `dry_run` mode to preview the organization plan without changing files

### 10. Delete files and folders

The file layer supports:

- Deleting one file
- Deleting multiple files
- Deleting folders

Folder deletion supports recursive and non-recursive behavior. Astra explicitly refuses to delete the root files directory.

## Backend API

The FastAPI routes expose the file system to the frontend and other clients.

### Listing and viewing

```text
GET /api/files
GET /api/files/{file_path}/preview
GET /api/files/{file_path}/open
GET /api/files/{file_path}/raw
```

### File operations

```text
POST /api/files/rename
POST /api/files/move
POST /api/files/delete
POST /api/files/delete-many
```

### Folder operations

```text
POST /api/files/folder
POST /api/files/folder/delete
```

### Related ingestion route

```text
POST /api/emails/{email_id}/attachments/save
```

## Agent Tools

The same file layer is also exposed to the agent through LangChain tools.

Key tools include:

- `list_user_files`
- `search_user_files`
- `open_user_file`
- `create_markdown_document`
- `create_pdf_document`
- `merge_markdown_files`
- `merge_pdf_files`
- `create_user_folder`
- `delete_user_folder`
- `rename_user_file`
- `move_user_file`
- `move_multiple_files`
- `move_files_in_folder`
- `categorize_user_files`
- `delete_user_file`
- `delete_multiple_files`

These tools let the agent talk about files in natural language and then turn those requests into structured operations.

The document-creation tools are especially useful when the user asks for:

- a brief
- a report
- a guide
- a summary document
- a merged Markdown note that should read logically
- a merged PDF packet with a title or cover page

## Examples

### Example 1: List all files

User intent:

```text
Show me my files
```

Typical behavior:

- Calls `list_user_files()`
- Returns files recursively from the root
- Includes folders, previews, domains, and counts

### Example 2: Search recent documents

User intent:

```text
Find recent pricing documents
```

Typical behavior:

- Calls `search_user_files("recent pricing documents")`
- Applies `documents` category
- Applies a recent timeframe
- Returns the most relevant matches

### Example 3: Open a PDF

User intent:

```text
Open Quarterly_Report.pdf
```

Typical behavior:

- Resolves the file inside the sandbox
- Returns a viewer payload with `kind: "pdf"`
- Opens the raw file URL for reading in the UI/browser

### Example 4: Open a markdown note

User intent:

```text
Open Acme_Pricing_Tiers.md
```

Typical behavior:

- Calls `open_user_file("Acme_Pricing_Tiers.md")`
- Returns viewer metadata and the raw file URL

### Example 5: Create a folder

User intent:

```text
Create a folder called Composer
```

Typical behavior:

- Calls `create_user_folder(name="Composer")`
- Creates the folder under the file root

### Example 6: Create a Markdown brief

User intent:

```text
Create a markdown document called Acme_Pricing_and_Helsinki_Guide.md in the root files folder. Give it a short introduction and two sections: one for Acme pricing, one for the Helsinki guide. Make it read like one logical document, not just pasted notes.
```

Typical behavior:

- Calls `create_markdown_document(...)`
- Uses section headings as source hints when full section bodies are not provided
- Pulls from matching source files through cached ingestion metadata
- Produces synthesized section text rather than dumping the full original files

### Example 7: Create a PDF brief

User intent:

```text
Create a PDF document called Q1_Sales_Brief.pdf with an introduction, an overview section, a key accounts section, and a next steps section.
```

Typical behavior:

- Calls `create_pdf_document(...)`
- Builds a structured PDF from ordered sections
- Produces a coherent report-style document rather than a raw file conversion

### Example 8: Merge multiple PDFs

User intent:

```text
Merge these PDFs into one packet and add a cover page explaining what is included.
```

Typical behavior:

- Calls `merge_pdf_files(...)`
- Creates a new PDF with a generated cover page
- Lists included source PDFs and merge order
- Appends original PDF pages after the cover page

### Example 9: Move multiple files

User intent:

```text
Move all pricing files into Sales
```

Possible backend behavior:

- Search or list matching files first
- Call `move_multiple_files([...], "Sales")`

### Example 10: Categorize by type

User intent:

```text
Categorize my files by type
```

Typical behavior:

- Calls `categorize_user_files(group_by="type")`
- Creates folders such as `Documents` and `Images`
- Moves files into those folders
- Returns a structured summary of created folders and moved files

### Example 11: Separate by meaning

User intent:

```text
Separate these files by meaning
```

Typical behavior:

- Calls `categorize_user_files(group_by="meaning")`
- Uses the domain router to choose buckets like `Sales`, `Travel`, or `Admin`
- Moves files into semantic folders

### Example 12: Preview organization by name

User intent:

```text
Organize my files by name, but show me the plan first
```

Typical behavior:

- Calls `categorize_user_files(group_by="name", dry_run=True)`
- Returns the proposed destination folder for each file
- Lets the agent confirm or apply the plan afterward

## Typical Workflows

### Document review workflow

1. Search for a document
2. Open it
3. Hand off the selected file to a separate LLM workflow if deeper analysis is needed

### Document authoring workflow

1. Ask for a Markdown or PDF brief
2. Provide a title, introduction, and section headings or section content
3. Let the agent synthesize a structured output document
4. Open the generated file from the file explorer

### Merge workflow

1. Choose the source Markdown or PDF files
2. Decide whether the goal is a logical summary document or a physical packet
3. Use Markdown merge for synthesized combined notes
4. Use PDF merge for a cover page plus original appended pages

### Inbox attachment workflow

1. Save an email attachment into `Downloads`
2. Auto-index metadata and domains
3. Open or search for it later from the file explorer

### Organization workflow

1. Create folders
2. Move files into those folders
3. Rename files for consistency
4. Delete duplicates or stale content

### Categorization workflow

1. Choose a grouping strategy such as `type`, `name`, or `meaning`
2. Preview the plan with `dry_run=True` when needed
3. Apply the categorization run
4. Refresh the explorer so the new folder structure is visible

## Metadata And Intelligence

Each file can carry lightweight metadata beyond basic file stats.

This includes:

- Summary points derived from cached ingestion
- Search text derived from extracted or synthesized document content
- Tags
- Domains
- Thumbnail labels and accents
- Time-aware filtering

There is also a metadata sidecar:

```text
.astra_meta.json
```

This is used to persist cached summaries, extracted search text, tags, and domains per directory without modifying the original file contents.

For generated documents, the same sidecar metadata can also reflect newly created or merged outputs after the file is written and re-ingested.

## Safety Constraints

The file system intentionally enforces several safety rules:

- Paths cannot escape the sandbox
- Unsupported files are ignored
- Root folder deletion is blocked
- Name collisions are resolved by deduping destination names
- Folder deletion can require recursive permission

These rules keep agent-driven file operations predictable and bounded.

## Current Frontend Behavior

The Tauri/React frontend currently supports:

- Browsing folders and files
- Sorting by name, type, size, and modification time
- Selecting files in the grid
- Showing file metadata

Depending on the UI surface, opening a file may:

- Open the raw file directly
- Render a dedicated viewer flow for supported content

The backend already provides enough structure to support richer viewers for:

- PDFs
- Markdown text
- Images

## Summary

The Astra file system is a sandboxed, agent-aware content layer rather than just a folder browser.

It supports:

- Storage
- Search
- Preview
- Open
- Structured document creation
- Logical Markdown merging
- Cover-page PDF merging
- Organize
- Categorize
- Delete
- Active-file conversational context

This makes it a core part of Astra's personal OS behavior: the assistant can find files, act on them safely, and use cached ingestion output as the first step of deeper LLM analysis when needed.
