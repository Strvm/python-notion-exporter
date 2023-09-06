import concurrent
import json
import logging
import multiprocessing
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from tqdm import tqdm


class ExportType:
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class ViewExportType:
    CURRENT_VIEW = "currentView"
    ALL = "all"


class NotionExporter:
    def __init__(
        self,
        token_v2: str,
        file_token: str,
        pages: dict,
        export_directory=None,
        flatten_export_file_tree=True,
        export_type=ExportType.MARKDOWN,
        current_view_export_type=ViewExportType.CURRENT_VIEW,
        include_files=False,
        recursive=True,
        workers=multiprocessing.cpu_count(),
    ):
        """
        Initializes the NotionExporter class.

        Args:
            token_v2 (str): The user's Notion V2 token.
            file_token (str): The user's file token for Notion.
            pages (dict): Dictionary of pages to be exported.
            export_directory (str, optional): Directory where exports will be saved. Defaults to the current directory.
            flatten_export_file_tree (bool, optional): If True, flattens the export file tree. Defaults to True.
            export_type (ExportType, optional): Type of export (e.g., MARKDOWN, HTML, PDF). Defaults to MARKDOWN.
            current_view_export_type (ViewExportType, optional): Type of view export (e.g., CURRENT_VIEW, ALL). Defaults to CURRENT_VIEW.
            include_files (bool, optional): If True, includes files in the export. Defaults to False.
            recursive (bool, optional): If True, exports will be recursive. Defaults to True.
            workers (int, optional): Number of worker threads for exporting. Defaults to the number of CPUs available.
        """

        self.export_name = f"export-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}"
        self.token_v2 = token_v2
        self.file_token = file_token
        self.include_files = include_files
        self.recursive = recursive
        self.pages = pages
        self.current_view_export_type = current_view_export_type
        self.flatten_export_file_tree = flatten_export_file_tree
        self.export_type = export_type
        self.export_directory = f"{export_directory}/" if export_directory else ""
        self.download_headers = {
            "content-type": "application/json",
            "cookie": f"file_token={self.file_token};",
        }
        self.query_headers = {
            "content-type": "application/json",
            "cookie": f"token_v2={self.token_v2};",
        }
        self.workers = workers
        os.makedirs(f"{self.export_directory}{self.export_name}", exist_ok=True)

    def _to_uuid_format(self, s):
        """
        Converts a string to UUID format.

        Args:
            s (str): The input string.

        Returns:
            str: The string in UUID format.
        """
        if "-" == s[8] and "-" == s[13] and "-" == s[18] and "-" == s[23]:
            return s
        return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"

    def _get_format_options(self, export_type: ExportType, include_files=False):
        """
        Retrieves format options based on the export type and whether to include files.

        Args:
            export_type (ExportType): Type of export (e.g., MARKDOWN, HTML, PDF).
            include_files (bool, optional): If True, includes files in the export. Defaults to False.

        Returns:
            dict: A dictionary containing format options.
        """
        format_options = {}
        if export_type == ExportType.PDF:
            format_options["pdfFormat"] = "Letter"

        if not include_files:
            format_options["includeContents"] = "no_files"

        return format_options

    def _export(self, id):
        """
        Initiates the export of a Notion page.

        Args:
            id (str): The ID of the Notion page.

        Returns:
            str: The task ID of the initiated export.
        """
        url = "https://www.notion.so/api/v3/enqueueTask"
        id = self._to_uuid_format(s=id)
        export_options = {
            "exportType": self.export_type,
            "locale": "en",
            "timeZone": "Europe/London",
            "collectionViewExportType": self.current_view_export_type,
            "flattenExportFiletree": self.flatten_export_file_tree,
        }

        # Update the exportOptions with format-specific options
        export_options.update(
            self._get_format_options(
                export_type=self.export_type, include_files=self.include_files
            )
        )

        payload = json.dumps(
            {
                "task": {
                    "eventName": "exportBlock",
                    "request": {
                        "block": {
                            "id": id,
                        },
                        "recursive": self.recursive,
                        "exportOptions": export_options,
                    },
                }
            }
        )

        response = requests.request(
            "POST", url, headers=self.query_headers, data=payload
        ).json()
        return response["taskId"]

    def _get_status(self, task_id):
        """
        Fetches the status of an export task.

        Args:
            task_id (str): The ID of the export task.

        Returns:
            dict: A dictionary containing details about the task status.
        """
        url = "https://www.notion.so/api/v3/getTasks"

        payload = json.dumps({"taskIds": [task_id]})

        response = requests.request(
            "POST", url, headers=self.query_headers, data=payload
        ).json()["results"]
        return response[0]

    def _download(self, url):
        """
        Downloads an exported file from a given URL.

        Args:
            url (str): The URL of the exported file.
        """
        response = requests.request("GET", url, headers=self.download_headers)
        file_name = url.split("/")[-1][100:]
        with open(
            f"{self.export_directory}{self.export_name}/{file_name}",
            "wb",
        ) as f:
            f.write(response.content)

    def _process_page(self, page_details):
        """
        Processes an individual Notion page for export.

        Args:
            page_details (tuple): Tuple containing the name and ID of the Notion page.

        Returns:
            dict: Details about the export status and any errors.
        """
        name, id = page_details
        task_id = self._export(id)

        status, state, error, pages_exported = self._wait_for_export_completion(
            task_id=task_id
        )
        if state == "failure":
            logging.error(f"Export failed for {name} with error: {error}")
            return {"state": state, "name": name, "error": error}

        export_url = status.get("status", {}).get("exportURL")
        if export_url:
            self._download(export_url)
        else:
            logging.warning(f"Failed to get exportURL for {name}")

        return {
            "state": state,
            "name": name,
            "exportURL": export_url,
            "pagesExported": pages_exported,
        }

    def _wait_for_export_completion(self, task_id):
        """
        Waits until a given export task completes or fails.

        Args:
            task_id (str): The ID of the export task.

        Returns:
            tuple: A tuple containing the status, state, error, and number of pages exported.
        """
        while True:
            status = self._get_status(task_id)

            if not status:
                time.sleep(1)
                continue
            state = status.get("state")
            error = status.get("error")
            if state == "failure" or status.get("status", {}).get("exportURL"):
                return (
                    status,
                    state,
                    error,
                    status.get("status", {}).get("pagesExported"),
                )
            time.sleep(1)

    def _unpack(self):
        """
        Unpacks and saves exported content from zip archives.
        """
        directory_path = f"{self.export_directory}{self.export_name}"
        for file in os.listdir(directory_path):
            if file.endswith(".zip"):
                full_file_path = os.path.join(directory_path, file)
                shutil.unpack_archive(full_file_path, directory_path, "zip")
                os.remove(full_file_path)

    def process(self):
        """
        Processes and exports all provided Notion pages.
        """
        logging.info(f"Exporting {len(self.pages)} pages...")

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            with tqdm(total=len(self.pages), dynamic_ncols=True) as pbar:
                futures = {
                    executor.submit(self._process_page, item): item
                    for item in self.pages.items()
                }
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result["state"] == "failure":
                        continue
                    name = result["name"]
                    pagesExported = result["pagesExported"]

                    pbar.set_postfix_str(
                        f"Exporting {name}... {pagesExported} pages already exported"
                    )
                    pbar.update(1)

        self._unpack()
