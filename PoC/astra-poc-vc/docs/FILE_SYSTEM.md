# Astra File System

This document explains how the file system works in `astra-poc-vc`, what kinds of files are supported, which operations are available, and how the agent and UI use the file layer.

## Overview

The Astra file system is a sandboxed document workspace used by the agent, the frontend file explorer, and the backend API.

At a high level, it provides:

- A safe root directory for user files
- File and folder listing
- Search by topic, file type, and timeframe
- Open and preview flows for text, PDFs, images, and videos
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

### Text-like files

- `.md`
- `.txt`
- `.json`
- `.csv`
- `.log`

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

### Video files

- `.mp4`
- `.mov`
- `.avi`
- `.mkv`
- `.webm`

### Office files

- `.doc`
- `.docx`
- `.xls`
- `.xlsx`
- `.ppt`
- `.pptx`

These are grouped into broad categories:

- `documents`
- `images`
- `videos`
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

- Text metadata preview
- PDF
- Image
- Video

The current backend does not read file bodies or generate built-in summaries. Text-like files expose metadata previews, and the UI can open the raw file URL when deeper inspection is needed.

### 4. Create folders

New folders can be created inside the sandbox, either:

- At the root
- Inside an existing subdirectory

### 5. Rename files

Files can be renamed safely within their current directory.

### 6. Move files

Astra supports several move patterns:

- Move one file to another folder
- Move multiple files in one operation
- Move all supported files from one folder into another folder

When name collisions happen, Astra automatically appends a numeric suffix instead of overwriting the destination file.

### 7. Categorize and separate files

Astra can now organize files into folders automatically through the agent tool layer.

Supported grouping strategies:

- `type` → `Documents`, `Images`, `Videos`, `Other`
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

### 8. Delete files and folders

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

### Example 6: Move multiple files

User intent:

```text
Move all pricing files into Sales
```

Possible backend behavior:

- Search or list matching files first
- Call `move_multiple_files([...], "Sales")`

### Example 7: Categorize by type

User intent:

```text
Categorize my files by type
```

Typical behavior:

- Calls `categorize_user_files(group_by="type")`
- Creates folders such as `Documents`, `Images`, and `Videos`
- Moves files into those folders
- Returns a structured summary of created folders and moved files

### Example 8: Separate by meaning

User intent:

```text
Separate these files by meaning
```

Typical behavior:

- Calls `categorize_user_files(group_by="meaning")`
- Uses the domain router to choose buckets like `Sales`, `Travel`, or `Admin`
- Moves files into semantic folders

### Example 9: Preview organization by name

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

- Summary points derived from file metadata
- Tags
- Domains
- Thumbnail labels and accents
- Time-aware filtering

There is also a metadata sidecar:

```text
.astra_meta.json
```

This is used to persist derived tags and domains per directory without modifying the original file contents.

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
- Text documents
- Images
- Videos

## Summary

The Astra file system is a sandboxed, agent-aware content layer rather than just a folder browser.

It supports:

- Storage
- Search
- Preview
- Open
- Organize
- Categorize
- Delete
- Active-file conversational context

This makes it a core part of Astra's personal OS behavior: the assistant can find files, act on them safely, and hand off richer analysis to a separate LLM layer when needed.
