import importlib
import logging
from pathlib import Path
import re
import sys
from urllib.parse import urlparse
import click
import requests
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from ruamel.yaml import YAML, scalarstring
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq


@click.pass_context
def die(ctx, msg, exception=None):
    if ctx.obj.get("BUNDLEUTILS_GBL_RAISE_ERRORS", False):
        logging.error(msg)
        raise exception or RuntimeError(f"ERROR: {msg}")
    else:
        sys.exit(f"ERROR: {msg}")


def get_config_file(filename):
    """Load a YAML config file from bundleutilspkg.data.configs."""
    if getattr(sys, "frozen", False):  # PyInstaller build
        base_path = Path(sys._MEIPASS) / "data/configs"  # type: ignore
    else:
        base_path = importlib.resources.files("bundleutilspkg.data.configs")  # type: ignore

    return base_path / filename


def join_url(url, path):
    """Join a base URL with a path, ensuring proper formatting."""
    return f"{url}".rstrip("/") + "/" + path.lstrip("/")


def find_controllers(obj):
    """
    Recursively find all online controllers based on the json obj.
    """
    controllers = []
    if isinstance(obj, dict):
        if "state" in obj:
            controllers.append(obj)
        for value in obj.values():
            controllers.extend(find_controllers(value))

    elif isinstance(obj, list):
        for item in obj:
            controllers.extend(find_controllers(item))
    return controllers


def is_truthy(value):
    """Check if a value is truthy."""
    if not value:
        return False
    return str(value).lower() in ["true", "1", "t", "y", "yes"]


def extract_name_from_url(url) -> str:
    # ensure URL is a valid URL format
    parsed = urlparse(str(url))

    if not all([parsed.scheme, parsed.netloc]) or not parsed.scheme.startswith(
        ("http", "https")
    ):
        die(f"Invalid URL format: {url}")

    # Check if the URL has a path
    if parsed.path and parsed.path != "/":
        return parsed.path.rstrip("/").split("/")[-1]
    # Otherwise, extract the first subdomain
    else:
        subdomain = parsed.netloc.split(".")[0]
        return subdomain


def lookup_details_from_url(url, ci_type="", ci_version="") -> tuple[str, str]:
    logging.debug(
        f"Using whoami to determine the type and version of the CloudBees CI instance at {url}"
    )
    if not ci_type or not ci_version:
        if not url.startswith("http"):
            die(f"URL {url} does not start with http(s)://")
        whoami_url = f"{url}/whoAmI"
        response = requests.get(whoami_url, timeout=5)
        response.raise_for_status()
        if not ci_type:
            logging.debug(f"Trying to determine CI type from URL {url}")
            # grep -oE "CloudBees CI (Managed Controller|Client Controller|Cloud Operations Center|Operations Center) [0-9.-]+-rolling"
            response_text = response.text
            # find the first match
            match = re.search(
                r"CloudBees CI (Managed Controller|Client Controller|Cloud Operations Center|Operations Center) [0-9.-]+-rolling",
                response_text,
            )
            if match:
                ci_type = match.group(1)
                # case switch the ci_type
                if ci_type == "Managed Controller":
                    ci_type = "mm"
                elif ci_type == "Client Controller":
                    ci_type = "cm"
                elif ci_type == "Cloud Operations Center":
                    ci_type = "oc"
                elif ci_type == "Operations Center":
                    ci_type = "oc-traditional"
                else:
                    die(f"Unknown CI type: {ci_type}")
                logging.debug(f"Type: {ci_type} (taken from remote)")
            else:
                die(f"Could not determine CI type from URL {url} - no match found")
        if not ci_version:
            logging.debug(f"Trying to determine CI version from URL {url}")
            # get headers from the whoami_url
            headers = response.headers
            logging.debug(f"Headers: {headers}")
            # get the x-jenkins header ignoring case and removing any carriage returns
            ci_version = headers.get("x-jenkins", headers.get("X-Jenkins", "")).replace(
                "\r", ""
            )
            logging.debug(f"Version: {ci_version} (taken from remote)")
    return ci_type, ci_version
