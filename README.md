# NotionExporter

## Description

`NotionExporter` is a Python class designed to simplify the process of exporting content from Notion. It provides an interface to configure, trigger, and download content exports from Notion. The class supports exporting content in various formats (Markdown, HTML, PDF) and also allows users to choose the scope of the export (current view vs. all content).

## Features

- Export content in **Markdown**, **HTML**, or **PDF** format.
- Configure the scope of your export: **current view** or **all content**.
- Option to include or exclude files in the export.
- Flatten the file tree structure upon export.
- Export multiple pages concurrently for faster processing.
- Monitor export progress with a progress bar.
- Automatically unpack zipped export files.

## Requirements

- Python 3.6+
- Dependencies:
  - `enum`
  - `os`
  - `json`
  - `requests`
  - `datetime`
  - `multiprocessing`
  - `logging`
  - `time`
  - `shutil`
  - `tqdm`

Make sure to install the necessary libraries using `pip`.

## Usage

1. **Initialization**:

   ```python
   exporter = NotionExporter(
       token_v2="YOUR_NOTION_TOKEN",
       file_token="YOUR_FILE_TOKEN",
       pages={"Page Name": "Page ID"},
       export_directory="path/to/save",
       flatten_export_file_tree=True,
       export_type=ExportType.MARKDOWN,
       current_view_export_type=ViewExportType.CURRENT_VIEW,
       include_files=True,
       recursive=True
   )
   ```

   You will need to get the `token_v2` and `file_token` values from your Notion cookies. The `pages` dictionary should contain pairs of `page_name: page_id` for each page you want to export.

2. **Process Exports**:

   ```python
   exporter.process()
   ```

   This will initiate the export, download, and unpacking processes for the pages defined.

For more details or any issues, please raise a ticket or contact the maintainers.