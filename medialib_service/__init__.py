import requests
import json
import config
from pathlib import Path

API_ROUTE = "media_receiving"


def send_result(payload: dict) -> tuple[str, bool]:
    """
    Send data to medialib servise and returns status info

    Returns: status string, success status (boolean)
    """
    if not config.use_medialib:
        raise ValueError("Need medialib parameters on config")
    API_URL = f"http://{config.ml_host}:{config.ml_port}/{API_ROUTE}/task/create/by_file"

    try:
        response = requests.post(API_URL, data=payload)
        if response.status_code == 201:
            return "OK", True
        else:
            print(f"Server error: ({response.status_code}):")
            return response.text, False

    except Exception as e:
        error_message = f"Request sending error: {e}"
        print(error_message)
        return error_message, False


def prepare_and_send_result(
    dm,
    parsed_tags: dict[str, set[str]],
    data: dict,
    outdir: Path,
):
    if config.use_medialib and not dm.skip_download:
        serializable_parsed_tags: dict[str, list[str]] = {
            category: list(parsed_tags[category]) for category in parsed_tags
        }
        raw_data: dict = dm.parser.get_raw_content_data()
        content_title = raw_data.get("name", "")
        content_description = raw_data.get("description", "")
        payload = {
            "origin_name": dm.parser.get_origin_name(),
            "origin_id": dm.parser.get_content_id(),
            "tags": json.dumps(serializable_parsed_tags),
            "file_path": str(dm.parser.get_output_filename(data, outdir)[1]),
            "title": content_title,
            "description": content_description,
            "mime_type": dm.parser.get_mime_type(),
        }
        status_message, is_ok = send_result(payload)
        if is_ok:
            file_path = Path(payload["file_path"])
            file_path.unlink()


def prepare_for_import(
    dm: DownloadManager,
    parsed_tags: dict[str, set[str]],
    file_path: Path,
    remove_if_success: bool,
):
    if config.use_medialib and not dm.skip_download:
        serializable_parsed_tags: dict[str, list[str]] = {
            category: list(parsed_tags[category]) for category in parsed_tags
        }
        raw_data: dict = dm.parser.get_raw_content_data()
        content_title = raw_data.get("name", "")
        content_description = raw_data.get("description", "")
        payload = {
            "origin_name": dm.parser.get_origin_name(),
            "origin_id": dm.parser.get_content_id(),
            "tags": json.dumps(serializable_parsed_tags),
            "file_path": file_path,
            "title": content_title,
            "description": content_description,
            "mime_type": dm.parser.get_mime_type(),
        }
        status_message, is_ok = send_result(payload)
        if is_ok and remove_if_success:
            file_path.unlink()


def check_exists(origin_name: str, origin_content_id: str) -> bool:
    """
    Check if source exists before downloading
    """
    if not config.use_medialib:
        raise ValueError("Need medialib parameters on config")
    API_URL = (
        f"http://{config.ml_host}:{config.ml_port}/{API_ROUTE}/origin/info"
    )
    payload = {
        "name": origin_name,
        "id": origin_content_id,
    }
    response = requests.get(API_URL, params=payload)
    json_data = response.json()
    if json_data["status"] == "found":
        url = json_data["url"]
        print(f"found content at http://{config.ml_host}:{config.ml_port}{url}")
        return True
    elif json_data["status"] == "not found":
        return False
    elif json_data["status"] == "error":
        error_message = json_data["message"]
        raise Exception(f"got error from medialib service: {error_message}")
    else:
        raise Exception("Unknown error")
