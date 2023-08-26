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

## Usage
1. **Download**:

   ```bash
   pip install python-notion-exporter
   ```


2. **Initialization**:

   ```python
   from python_notion_exporter import NotionExporter
   
   # Important to run in __main__ or in a method due to multiprocessing.
   if __name__ == "__main__":
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

## Needed Cookies

To export anything from Notion, one needs to authenticate oneself with some
Cookies (like a browser would). These cookies are called `token_v2` and
`file_token`. They are set on all requests of a logged in user when using the
Notion web-app.


### How to retrieve the Cookies?

- Go to [notion.so](https://notion.so).
- Log in with your account.
- Open the developer tools of your browser, open Application > Storage > Cookies
  (Chrome); Storage tab (Firefox).
- Copy the value of the Cookies called `token_v2` and `file_token` and paste
  them somewhere safe.
- ⚠️ If you don't find `file_token`, you need to have at least had exported a file manually once.
- Those cookies have a **1 year validity**, so you don't need to do this often.

2. **Process Exports**:

   ```python
   exporter.process()
   ```

   This will initiate the export, download, and unpacking processes for the pages defined.

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

For more details or any issues, please raise a ticket or contact the maintainers.