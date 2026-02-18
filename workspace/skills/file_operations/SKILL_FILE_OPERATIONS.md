---
name: File Operations
description: Write, list, search, and inspect files/directories in the local filesystem.
module: builtin_tools.file_ops
tools:
  - write_file
  - list_directory
  - search_files
  - file_info
---

# File Operations Skill

Bootstrap tool `read_file` is always available before skill activation.
This skill adds mutation and discovery operations.

## `write_file`
- Required: `path`, `content`
- Creates/overwrites UTF-8 text file

## `list_directory`
- Required: `path`
- Optional: `recursive` (default `false`)
- Returns entries with type and file size where available

## `search_files`
- Required: `path`, `pattern`
- Optional: `max_results` (default `20`)
- Pattern uses glob semantics (`*.py`, `**/*.md`)

## `file_info`
- Required: `path`
- Returns metadata: absolute path, type, size, timestamps
