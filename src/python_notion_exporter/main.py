import enum
import json
import logging
import multiprocessing
import os
import shutil
import time
from datetime import datetime
from multiprocessing import Pool, freeze_support

import requests
from tqdm import tqdm


class ExportType(enum.StrEnum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class ViewExportType(enum.StrEnum):
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
        if "-" == s[8] and "-" == s[13] and "-" == s[18] and "-" == s[23]:
            return s
        return f"{s[:8]}-{s[8:12]}-{s[12:16]}-{s[16:20]}-{s[20:]}"

    def _get_format_options(self, export_type: ExportType, include_files=False):
        format_options = {}
        if export_type == ExportType.PDF:
            format_options["pdfFormat"] = "Letter"

        if not include_files:
            format_options["includeContents"] = "no_files"

        return format_options

    def _export(self, id):
        url = "https://www.notion.so/api/v3/enqueueTask"
        id = self._to_uuid_format(s=id)
        export_options = {
            "exportType": self.export_type.value,
            "locale": "en",
            "timeZone": "Europe/London",
            "collectionViewExportType": self.current_view_export_type.value,
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
        url = "https://www.notion.so/api/v3/getTasks"

        payload = json.dumps({"taskIds": [task_id]})

        response = requests.request(
            "POST", url, headers=self.query_headers, data=payload
        ).json()["results"]
        return response[0]

    def _download(self, url):
        response = requests.request("GET", url, headers=self.download_headers)
        file_name = url.split("/")[-1][100:]
        with open(
            f"{self.export_directory}{self.export_name}/{file_name}",
            "wb",
        ) as f:
            f.write(response.content)

    def _process_page(self, page_details):
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
        """Helper method to wait until the export is complete or failed."""
        while True:
            status = self._get_status(task_id)
            # print(status)

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
        directory_path = f"{self.export_directory}{self.export_name}"
        for file in os.listdir(directory_path):
            if file.endswith(".zip"):
                full_file_path = os.path.join(directory_path, file)
                shutil.unpack_archive(full_file_path, directory_path, "zip")
                os.remove(full_file_path)

    def process(self):
        logging.info(f"Exporting {len(self.pages)} pages...")
        with Pool(processes=self.workers) as pool:
            with tqdm(total=len(self.pages), dynamic_ncols=True) as pbar:
                for result in pool.imap_unordered(
                    self._process_page, self.pages.items()
                ):
                    if result["state"] == "failure":
                        continue
                    name = result["name"]
                    pagesExported = result["pagesExported"]

                    pbar.set_postfix_str(
                        f"Exporting {name}... {pagesExported} pages already exported"
                    )
                    pbar.update(1)

        self._unpack()


if __name__ == "__main__":
    freeze_support()
