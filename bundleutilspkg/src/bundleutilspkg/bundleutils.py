from contextlib import contextmanager
from enum import Enum, auto
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import uuid
import bundleutilspkg.utils as utilz
import jsonpatch
import jsonpointer
import zipfile
import requests
import base64
import glob
import io
import os
import click
import locale
import logging
import re
import sys
from importlib.metadata import metadata, PackageNotFoundError
from collections import OrderedDict, defaultdict
from dataclasses import dataclass
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from ruamel.yaml import YAML, scalarstring
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq
from bundleutilspkg.yaml_merger import YAMLMerger
from bundleutilspkg.server_manager import JenkinsServerManager
from urllib.parse import urlparse
from bundleutilspkg._version import __version__

# Set the locale to C to ensure consistent sorting
locale.setlocale(locale.LC_ALL, "C")
# Set the default encoding to UTF-8
os.environ["PYTHONUTF8"] = "1"

yaml = YAML(typ="rt")

script_name = os.path.basename(__file__).replace(".py", "")
script_name_upper = script_name.upper()

plugin_json_url_path = (
    "/manage/pluginManager/api/json?pretty&depth=1&tree=plugins[*[*]]"
)
controllers_url_path = "/api/json?depth=1&pretty&pretty&tree=jobs[url,online,state,endpoint,jobs[url,online,state,endpoint,jobs[url,online,state,endpoint,jobs[url,online,state,endpoint]]]]"
validate_url_path = "/casc-bundle-mgnt/casc-bundle-validate"
get_effective_bundle_path = "/casc-bundle/get-effective-bundle?bundle="
empty_bundle_strategies = ["fail", "delete", "noop"]
default_bundle_api_version = "2"
default_keys_to_scalars = ["systemMessage", "script", "description"]
default_empty_bundle_strategy = "delete"
default_bundle_detection_pattern = r"^main-([a-z0-9\-]+)-drift(?:__[a-zA-Z0-9\-]+)*$"
default_config_base = ".bundleutils"

bundle_yaml_keys = {
    "jcasc": "jenkins.yaml",
    "plugins": "plugins.yaml",
    "catalog": "plugin-catalog.yaml",
    "rbac": "rbac.yaml",
    "items": "items.yaml",
    "variables": "variables.yaml",
}
selector_pattern = re.compile(r"\{\{select\s+\"([^\"]+)\"\s*\}\}")
BUNDLEUTILS_CREDENTIAL_DELETE_SIGN = "PLEASE_DELETE_ME"
BUNDLEUTILS_AUDIT_FIXED_VERSION = "BUNDLEUTILS_AUDIT_FIXED_VERSION"


# Adopted from https://stackoverflow.com/a/35804945/1691778
# Adds a new logging method to the logging module
def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)


# Create the TRACE level
addLoggingLevel("TRACE", logging.DEBUG - 5)


def to_env(key):
    return f"BUNDLEUTILS_{key.upper()}"


def long_opt(key):
    """Helper function to create a click option with the key as the name."""
    return f"--{key.lower().replace('_', '-')}"


class Key(Enum):
    API_PATH = ("-P", [], "Path to the API endpoint to call", 1)
    API_DATA_FILE = ("-d", [], "The data to post to the API endpoint", 1)
    API_OUT_FILE = ("-o", [], "The output file to write the API response to", 1)
    AUDIT_SOURCE_DIR = (
        "-s",
        [],
        "The source directory for the YAML documents to audit",
        1,
    )
    AUDIT_TARGET_DIR = (
        "-t",
        [],
        "The target directory for the audited YAML documents",
        1,
    )
    AUDIT_HASH_SEED = (
        "-H",
        [],
        """
    Optional prefix for the hashing process.

    NOTE: Ideally, this should be a secret value that is not shared with anyone. Changing this value will result in different hashes.""",
        1,
    )

    AUDIT_HASH = (
        "-n",
        [],
        "Replace sensitive data with its ${THIS_IS_THE_SECRET} equivalent",
        1,
        True,
    )
    PASSWORD = ("-p", [], "Password for basic authentication")
    URL = ("-U", [to_env("JENKINS_URL"), "JENKINS_URL"], "The URL to interact with")
    OC_URL = ("-O", [], "The URL of the OC")
    USERNAME = ("-u", [], "Username for basic authentication")
    BUNDLE_NAME = (
        "-N",
        [],
        "The bundle name based on the instance name and optionally version",
    )
    BUNDLES_BASE = ("-b", [], "The base directory for the bundles")
    CI_INSTANCE_NAME = ("-n", [], "The name of the CloudBees instance")
    CI_MAX_START_TIME = (
        "-x",
        [],
        "The maximum time to wait for the CI to start (in seconds)",
    )
    CI_SERVER_HOME = (
        "-H",
        [],
        "Defaults to /tmp/ci_server_home/<ci_type>/<ci_version>",
    )
    CI_SETUP_SOURCE_DIR = (
        "-s",
        [],
        "The bundle to be validated - startup will use the plugins from here",
        2,
    )
    CI_BUNDLE_TEMPLATE = (
        "-T",
        [],
        "Path to a template bundle used to start the test server - defaults to in-built template",
    )
    CI_FORCE = ("-f", [], "Force download of the WAR file even if exists", 1, True)
    CI_TYPE = ("-t", [], "The type of the CloudBees instance")
    CI_VERSION = ("-v", [], "The version of the CloudBees instance")
    CONFIG_KEY = (
        "-K",
        [],
        "Returns value if key provided (error if not found), or k=v when used as flag",
    )
    CONFIG = ("-c", [], "The transformation config to use")
    CONFIGS_BASE = ("-C", [], "The directory containing the transformation config(s)")
    DRY_RUN = ("-d", [], "Print the merged transform config and exit", 0, True)
    EXTRACT_BUNDLES_DIR = (
        "-b",
        [],
        "Optional directory containing the bundles or PWD",
        1,
    )
    EXTRACT_PATTERN = ("-p", [], "Optional pattern to match against", 1)
    EXTRACT_STRING = (
        "-s",
        [],
        "The string to test (e.g. a feature/testing-controller-a or main-controller-a-drift)",
        1,
    )
    FETCH_IGNORE_ITEMS = (
        "-I",
        [],
        f"Do not fetch the computationally expensive items.yaml",
        1,
        True,
    )
    FETCH_KEYS_TO_SCALARS = (
        "-k",
        [],
        f"Comma-separated list of yaml dict keys to convert to \"|\" type strings instead of quoted strings, defaults to '{','.join(default_keys_to_scalars)}'",
        1,
    )
    FETCH_LOCAL_OFFLINE = (
        "-O",
        [],
        f"Save the export and plugin data to <target-dir>-offline",
        2,
    )
    FETCH_LOCAL_PATH = ("-P", [], f"The path to fetch YAML from", 2)
    FETCH_LOCAL_PLUGIN_JSON_PATH = (
        "-M",
        [],
        f"The path to fetch JSON file from (found at {plugin_json_url_path})",
        2,
    )
    FETCH_TARGET_DIR = (
        "-t",
        [],
        "The target directory for the fetched YAML documents",
        1,
    )
    GBL_APPEND_VERSION = (
        "-a",
        [],
        "Append the current version to the bundle directory",
        1,
        True,
    )
    GBL_URL_BASE_PATTERN = (
        "-p",
        [],
        """
                            The URL pattern to deduce the URL from inside a bundle directory

                            \b
                            Uses NAME as a placeholder, e.g.
                            - "https://example.com/NAME"
                            - "https://NAME.example.com"
                            """,
        1,
    )
    DEDUCED_URL = ("-p", [], "NOT USED AS AN OPTION - holder for the deduced url", 1)
    GBL_INTERACTIVE = ("-i", [], "Run in interactive mode", 1, True)
    GBL_LOG_LEVEL = ("-l", [], "The log level", 1)
    GBL_RAISE_ERRORS = ("-e", [], "Raise errors instead of printing them", 1, True)
    LAST_KNOWN_VERSION = (
        "-L",
        [],
        "The last known version of the bundle when current version is not available",
    )
    MERGE_API_VERSION = (
        "-a",
        [],
        f"Optional apiVersion. Defaults to {default_bundle_api_version}",
        1,
    )
    MERGE_BUNDLES = ("-b", [], "The bundles to be rendered", 1)
    MERGE_CONFIG = ("-m", [], "An optional custom merge config file if needed", 1)
    MERGE_FILES = ("-f", [], "The files to merge", 1)
    MERGE_DIFFCHECK = ("-d", [], "Optionally perform bundleutils diff", 1)
    MERGE_OUTDIR = ("-o", [], "The target for the merged bundle", 1)
    MERGE_TRANSFORM = (
        "-T",
        [],
        "Optionally transform using the transformation configs",
        1,
    )
    MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR = (
        "-S",
        [],
        "The source directory for the diff check",
        1,
    )
    MERGE_TRANSFORM_SOURCE_DIR = (
        "-s",
        [],
        "The source directory for the transformation",
        1,
    )
    MERGE_TRANSFORM_TARGET_DIR = (
        "-t",
        [],
        "The target directory for the transformed bundle",
        1,
    )
    MERGE_USE_PARENT = (
        "-p",
        [],
        "Optionally use the (legacy) parent key to work out which bundles to merge",
        1,
        True,
    )
    # The strategy for handling warnings when fetching the catalog.
    # These warning make the yaml purposely invalid so that people cannot simply use the output
    # without fixing the issues.
    # The options are from the PluginPluginCatalogWarningsStrategy enum below.
    # e.g.
    # --- There are Beekeeper warnings. This makes the bundle export a "best effort".
    # --- Exported plugin catalog and plugins list might be incorrect and might need manual fixing before use.
    # --- Pipeline: Groovy Libraries (pipeline-groovy-lib). Version 740.va_2701257fe8d is currently installed but version 727.ve832a_9244dfa_ is recommended for this version of the product.
    PLUGINS_CATALOG_WARNINGS_STRATEGY = (
        "-C",
        [],
        f"Strategy for handling beekeeper warnings in the plugin catalog",
        1,
    )
    PLUGINS_JSON_LIST_STRATEGY = (
        "-j",
        [],
        f"Strategy for creating list from the plugins json",
    )
    PLUGINS_JSON_MERGE_STRATEGY = (
        "-J",
        [],
        f"Strategy for merging plugins from list into the bundle",
    )
    PLUGINS_USE_CAP = (
        "-c",
        [],
        f"Use the envelope.json from the war file to remove CAP plugin dependencies",
        1,
        True,
    )

    SANITIZE_PLUGINS_PIN_PLUGINS = (
        "-p",
        [],
        "Add versions to 3rd party plugins (only available for apiVersion 2)",
        2,
        True,
    )
    SANITIZE_PLUGINS_CUSTOM_URL = (
        "-u",
        [],
        "Add a custom URL, e.g. http://plugins-repo/plugins/PNAME/PVERSION/PNAME.hpi",
        2,
    )

    SHELL = ("-s", [], "The shell to generate completion script for")
    STRICT = (
        "-S",
        [],
        "Fail when referencing non-existent files - warn otherwise",
        0,
        True,
    )
    TRANSFORM_SOURCE_DIR = (
        "-s",
        [],
        "The source directory for the YAML documents to transform",
        1,
    )
    TRANSFORM_TARGET_DIR = (
        "-t",
        [],
        "The target directory for the transformed YAML documents",
        1,
    )
    UPDATE_BUNDLE_TARGET_DIR = (
        "-t",
        [],
        "The target directory to update the bundle.yaml file (defaults to CWD)",
        2,
    )
    UPDATE_BUNDLE_DESCRIPTION = ("-d", [], "Optional description for the bundle", 2)
    UPDATE_BUNDLE_OUTPUT_SORTED = (
        "-o",
        [],
        "Optional place to put the sorted yaml string used to create the version",
        2,
    )
    UPDATE_BUNDLE_EMPTY_BUNDLE_STRATEGY = (
        "-e",
        [],
        "Optional strategy for handling empty bundles",
        2,
    )
    UPDATE_BUNDLE_RECURSIVE = (
        "-r",
        [],
        "Update recursively on all bundles found from target dir",
        2,
        True,
    )
    VALIDATE_EXTERNAL_RBAC = (
        "-r",
        [],
        "Path to an external rbac.yaml from an operations center bundle",
        1,
    )
    VALIDATE_IGNORE_WARNINGS = (
        "-w",
        [],
        "Do not fail if warnings are found in validation",
        1,
        True,
    )
    VALIDATE_SOURCE_DIR = (
        "-s",
        [],
        "The source directory for the YAML documents to validate",
        1,
    )

    def __init__(
        self,
        short: str,
        envvar: list[str],
        help_text: str,
        strip_parts: int = 0,
        is_Flag: bool = False,
    ):
        parts = self.name.split("_")
        self.short = short
        self.arg = "_".join(parts[strip_parts:]).lower()
        self.long = f"--{self.arg.replace('_', '-')}"
        if is_Flag:
            self.long = f"{self.long}/--no-{self.arg.replace('_', '-')}"
        self.envvar = envvar or [to_env(self.name)]
        self.help = f"{help_text} ({self.envvar[0]})"


def option_for(key: Key, **extra_kwargs):
    # if help is not provided, use the key's help text
    if "help" not in extra_kwargs:
        extra_kwargs["help"] = f"{key.help}"
    else:
        extra_kwargs["help"] = extra_kwargs["help"] + f" ({key.envvar[0]})"

    def decorator(func):
        return click.option(
            key.short,
            key.long,
            envvar=key.envvar,
            **extra_kwargs,
        )(func)

    return decorator


# internal cache
internal_cache = {}


def die(msg, exception=None):
    if utilz.is_truthy(_get(Key.GBL_RAISE_ERRORS, False)):
        logging.error(msg)
        raise exception or RuntimeError(f"ERROR: {msg}")
    else:
        sys.exit(f"ERROR: {msg}")


# - 'FAIL' - fail the command if there are warnings
# - 'COMMENT' - add a comment to the yaml with the warnings
class PluginCatalogWarningsStrategy(Enum):
    FAIL = auto()
    COMMENT = auto()


class PluginJsonMergeStrategy(Enum):
    ALL = auto()
    DO_NOTHING = auto()
    ADD_ONLY = auto()
    ADD_DELETE = auto()
    ADD_DELETE_SKIP_PINNED = auto()

    def should_delete(self):
        return (
            self == PluginJsonMergeStrategy.ADD_DELETE
            or self == PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED
        )

    def skip_pinned(self):
        return self == PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED


class PluginJsonListStrategy(Enum):
    AUTO = auto()
    ROOTS = auto()
    ROOTS_AND_DEPS = auto()
    ALL = auto()


def ordered_yaml_dump(data):
    """Convert YAML object to a consistent ordered string."""
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 80
    yaml.preserve_quotes = True

    def recursive_sort(obj):
        """Recursively sort dictionary keys to ensure a consistent order."""
        if isinstance(obj, (CommentedMap, dict)):
            return OrderedDict(sorted((k, recursive_sort(v)) for k, v in obj.items()))
        elif isinstance(obj, (CommentedSeq, list)):
            # Sort lists of dictionaries by the 'name' key if present
            if all(isinstance(i, dict) and "name" in i for i in obj):
                return sorted(obj, key=lambda x: x["name"])
            return [recursive_sort(i) for i in obj]
        return obj

    ordered_data = recursive_sort(data)
    return printYaml(ordered_data, True, yaml)


def generate_collection_uuid(target_dir, yaml_files, output_sorted=None):
    """Generate a stable UUID for a collection of YAML files."""
    yaml = YAML()
    combined_yaml_data = OrderedDict()

    for file in sorted(yaml_files):  # Ensure consistent file order
        file_path = Path(target_dir) / file
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.load(f)
                if data:  # Only merge non-empty files
                    combined_yaml_data[file_path.name] = (
                        data  # Use filename as key to preserve structure
                    )

    ordered_yaml_str = ordered_yaml_dump(combined_yaml_data)
    yaml_hash = hashlib.sha256(ordered_yaml_str.encode()).hexdigest()
    if output_sorted:
        if not os.path.exists(output_sorted):
            if output_sorted.endswith(".yaml"):
                with open(output_sorted, "w", encoding="utf-8") as f:
                    f.write("")
            else:
                os.makedirs(output_sorted)
        # if output_sorted is a directory, print each file to a separate file
        if os.path.isdir(output_sorted):
            for file in os.listdir(output_sorted):
                os.remove(os.path.join(output_sorted, file))
            # copy the target_dir bundle.yaml file to the output directory
            target_bundle_yaml = Path(target_dir) / "bundle.yaml"
            if target_bundle_yaml.exists():
                shutil.copy(target_bundle_yaml, output_sorted)
            # copy other files
            for file_name, data in combined_yaml_data.items():
                with open(
                    os.path.join(output_sorted, file_name), "w", encoding="utf-8"
                ) as f:
                    logging.info(f"Writing {file_name} sorted YAML to {output_sorted}")
                    f.write(ordered_yaml_dump(data))
            # run _update_bundle without the --output-sorted flag
            # to update the bundle.yaml file with the new UUID
            announce(f"Updating the sorted bundle.yaml with UUID: {yaml_hash}")
            _update_bundle(output_sorted)
        else:
            with open(output_sorted, "w", encoding="utf-8") as f:
                logging.info(
                    f"Writing {yaml_hash} ({uuid.UUID(yaml_hash[:32])}) sorted YAML to {output_sorted}"
                )
                f.write(ordered_yaml_str)
    return str(uuid.UUID(yaml_hash[:32]))  # Convert first 32 chars to UUID format


def get_value_from_enum(value, my_enum):
    try:
        return my_enum[value]
    except KeyError:
        die(
            f"Invalid value: {value} for {my_enum}. Must be one of {[e.name for e in my_enum]}"
        )


def get_name_from_enum(my_enum):
    return [x.name for x in my_enum]


def _deduce_bundle_name(ci_version) -> tuple[str, str]:
    # if bundle_name is set, expect the instance name to be set as well
    bundle_name = _get(Key.BUNDLE_NAME, required=False, allow_interactive=False)
    if bundle_name:
        instance_name = _deduce_ci_instance_name()
        if not instance_name:
            die("No instance name provided to deduce the bundle name.")
        return instance_name, bundle_name

    # deduce instance name
    instance_name = _deduce_ci_instance_name()
    bundle_name = instance_name

    # optional version
    append_version = utilz.is_truthy(_get(Key.GBL_APPEND_VERSION))
    if append_version:
        ci_version = _deduce_version(ci_version)
        bundle_name = f"{instance_name}-{ci_version}"

    _set(Key.BUNDLE_NAME, bundle_name)
    return instance_name, bundle_name


def _deduce_ci_instance_name(ci_instance_name=None) -> str:
    ci_instance_name = _get(
        Key.CI_INSTANCE_NAME, ci_instance_name, required=False, allow_interactive=False
    )
    if not ci_instance_name:
        url = _get(Key.URL, required=False)
        if not url:
            die("No ci_instance_name provided or URL to extract a version from.")
        ci_instance_name = utilz.extract_name_from_url(url)
        _set(Key.CI_INSTANCE_NAME, ci_instance_name)

    return ci_instance_name


def _deduce_version(ci_version=None) -> str:
    ci_version = _get(
        Key.CI_VERSION, ci_version, required=False, allow_interactive=False
    )
    if not ci_version:
        url = _get(Key.URL, required=False)
        if not url:
            die("No ci_version provided or URL to extract a version from.")
        try:
            ci_type, ci_version = utilz.lookup_details_from_url(url)
            _set(Key.CI_VERSION, ci_version)
            # set the CI type if not already set
            curr_ci_type = _get(Key.CI_TYPE, required=False, allow_interactive=False)
            if not curr_ci_type:
                _set(Key.CI_TYPE, ci_type)
        except requests.RequestException as e:
            # fall back to the interactive mode
            ci_version = _get(Key.CI_VERSION)

    return str(ci_version)


def _deduce_type(ci_type=None) -> str:
    ci_type = _get(Key.CI_TYPE, ci_type, required=False, allow_interactive=False)
    if not ci_type:
        url = _get(Key.URL, required=False)
        if not url:
            die("No ci_type provided or URL to extract a type from.")
        try:
            ci_type, ci_version = utilz.lookup_details_from_url(url)
            _set(Key.CI_TYPE, ci_type)
            # set the CI version if not already set
            curr_ci_version = _get(
                Key.CI_VERSION, required=False, allow_interactive=False
            )
            if not curr_ci_version:
                _set(Key.CI_VERSION, ci_version)
        except requests.RequestException as e:
            # fall back to the interactive mode
            ci_type = _get(Key.CI_TYPE)

    return str(ci_type)


@click.pass_context
def _add_default_dirs_if_necessary(ctx, url, ci_version, passed_dirs):
    """
    Add default paths based on the URL and potentially version.
    """
    bundles_base = str(_get(Key.BUNDLES_BASE))
    instance_name, bundle_name = _deduce_bundle_name(ci_version)

    # check if we need to look for the last known version
    append_version = utilz.is_truthy(_get(Key.GBL_APPEND_VERSION))

    # set the bundle name and last known version
    last_known_version = ""
    if append_version:
        if not os.path.exists(bundle_name):
            # find the last directory that matches the pattern "{instance_name}-x.x.x.x"
            regex = re.compile(rf"^{instance_name}-[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$")
            for dir in reversed(
                sorted(os.listdir(bundles_base), key=lambda x: x.lower())
            ):
                if regex.match(dir):
                    last_known_version = dir
                    break
    _set(Key.LAST_KNOWN_VERSION, last_known_version)

    # get target dir values
    bundle_target_dir = os.path.join(bundles_base, bundle_name)
    bundle_target_dir = _get_relative_path(bundle_target_dir, bundles_base)

    default_dirs = {}
    default_dirs[Key.FETCH_TARGET_DIR] = f"target/fetched/{bundle_name}"
    default_dirs[Key.TRANSFORM_SOURCE_DIR] = default_dirs[Key.FETCH_TARGET_DIR]
    default_dirs[Key.TRANSFORM_TARGET_DIR] = bundle_target_dir
    default_dirs[Key.CI_SETUP_SOURCE_DIR] = default_dirs[Key.TRANSFORM_TARGET_DIR]
    default_dirs[Key.VALIDATE_SOURCE_DIR] = default_dirs[Key.TRANSFORM_TARGET_DIR]
    default_dirs[Key.MERGE_OUTDIR] = f"target/merged/{bundle_name}"
    default_dirs[Key.MERGE_TRANSFORM_SOURCE_DIR] = default_dirs[Key.MERGE_OUTDIR]
    default_dirs[Key.MERGE_TRANSFORM_TARGET_DIR] = f"target/expected/{bundle_name}"
    default_dirs[Key.MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR] = bundle_target_dir
    default_dirs[Key.AUDIT_SOURCE_DIR] = default_dirs[Key.FETCH_TARGET_DIR]
    default_dirs[Key.AUDIT_TARGET_DIR] = bundle_target_dir

    for key in passed_dirs:
        value = passed_dirs[key]
        _get(key, value, default_dirs[key])


# TODO: refactor this to use the ctx object
def _todo_replace_placeholders():
    # loop through the env vars and replace any placeholders
    placeholder_re = re.compile(r"\$\{([^\}]+)\}")
    for key, value in os.environ.items():
        if key.startswith("BUNDLEUTILS_"):
            new_value = placeholder_re.sub(
                lambda m: os.environ.get(m.group(1), ""), value
            )
            if new_value != value:
                logging.info(f"Replacing {key}={value} with {new_value}")
                os.environ[key] = new_value


@click.pass_context
def _determine_transformation_config(
    ctx, url: str, config: str, instance_name: str = ""
) -> str:
    """Determine the transformation config file based on the URL and context."""
    # base dirs
    cwd = os.getcwd()
    config_base = _get(Key.CONFIGS_BASE) or default_config_base
    config_base = _get_relative_path(config_base, cwd)
    bundles_base = _get(Key.BUNDLES_BASE)
    bundles_base = _get_relative_path(bundles_base, cwd)
    command_name = ctx.command.name
    config_files = []

    if config == "auto":
        config = ""
        # instance details
        ci_version = _deduce_version()
        ci_type = _deduce_type()
        instance_name, bundle_name = _deduce_bundle_name(ci_version)
        if instance_name and ci_version:
            config_files.append(f"{command_name}-{instance_name}-{ci_version}.yaml")
        if ci_type and ci_version:
            config_files.append(f"{command_name}-{ci_type}-{ci_version}.yaml")
        if instance_name:
            config_files.append(f"{command_name}-{instance_name}.yaml")
        if ci_type:
            config_files.append(f"{command_name}-{ci_type}.yaml")
        if ci_version:
            config_files.append(f"{command_name}-{ci_version}.yaml")

    if config:
        return_config = ""
        # if config starts with "int:" then it is an internal config
        if config.startswith("int:"):
            return_config = utilz.get_config_file(config[4:])
        else:
            return_config = _get_relative_path(config, cwd)
        if not os.path.exists(return_config):
            die(f"Transformation config file {config} does not exist.")
        logging.info(f"Using provided transformation configs: {return_config}")
        return str(return_config)

    # checking possible configs
    config_files.append(f"{command_name}.yaml")

    found = ""
    for config_file in config_files:
        msg = ""
        for dir_to_check in [bundles_base, config_base]:
            config = os.path.join(dir_to_check, config_file)
            msg = f"Checking for config file: "
            if os.path.exists(config):
                msg = f"{msg} (x)"
                if not found:
                    found = config
            else:
                msg = f"{msg}    "
            logging.debug(f"{msg} {config}")
    for config_file in config_files:
        # check internal config base
        config = utilz.get_config_file(config_file)
        msg = f"Checking for config file: "
        if os.path.exists(config):
            msg = f"{msg} (x)"
            if not found:
                found = config
        else:
            msg = f"{msg}    "
        logging.debug(f"{msg} {config}")
    logging.info(f"Using config file: {found}")
    return found


@click.group(invoke_without_command=True)
@option_for(
    Key.GBL_LOG_LEVEL,
    default="INFO",
    type=click.Choice(["TRACE", "DEBUG", "INFO", "WARNING"]),
)
@option_for(Key.GBL_RAISE_ERRORS, default="False", type=click.BOOL)
@option_for(Key.GBL_INTERACTIVE, default="False", type=click.BOOL)
@option_for(Key.GBL_APPEND_VERSION, default="False", type=click.BOOL)
@option_for(
    Key.BUNDLES_BASE,
    type=click.Path(file_okay=False, dir_okay=True),
    default=os.getcwd(),
)
@option_for(Key.GBL_URL_BASE_PATTERN, required=False)
@click.pass_context
def bundleutils(
    ctx,
    log_level,
    raise_errors,
    interactive,
    append_version,
    bundles_base,
    url_base_pattern,
):
    """A tool to fetch and transform YAML documents."""
    # inject PYTHONUTF8=1 into the environment
    os.environ["PYTHONUTF8"] = "1"
    ctx.ensure_object(dict)
    ctx.max_content_width = 120
    _set(Key.GBL_INTERACTIVE, interactive)
    _set(Key.GBL_RAISE_ERRORS, raise_errors)
    _set(Key.GBL_APPEND_VERSION, append_version)
    _set(Key.BUNDLES_BASE, bundles_base)
    log_level = _get(Key.GBL_LOG_LEVEL, log_level)
    logging.getLogger().setLevel(str(log_level))
    logging.debug(f"Set log level to: {log_level}")

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    else:
        _set(Key.DEDUCED_URL, "")
        if url_base_pattern:
            cwd = os.getcwd()
            # if current dir contains a bundle.yaml file, set the URL base pattern
            bundle_yaml = os.path.join(cwd, "bundle.yaml")
            if os.path.exists(bundle_yaml):
                base_name = os.path.basename(cwd)
                deduced_url = url_base_pattern.replace("NAME", base_name)
                _set(Key.DEDUCED_URL, deduced_url)
                logging.debug(
                    f"AUTO_URL: Using {Key.GBL_URL_BASE_PATTERN.envvar[0]} '{url_base_pattern}'."
                )
                logging.debug(
                    f"AUTO_URL: Deduced URL {deduced_url} from bundle directory {base_name}."
                )
                # get current directory
                if bundles_base == os.getcwd():
                    parent_dir = os.path.dirname(cwd)
                    logging.debug(
                        f"AUTO_URL: Switching to {parent_dir} and setting {Key.BUNDLES_BASE.envvar[0]} accordingly."
                    )
                    _set(Key.BUNDLES_BASE, parent_dir)
                    os.chdir(parent_dir)


def yaml2dict(yamlFile):
    dict_res = {}
    with open(yamlFile, "r", encoding="utf-8") as fp:
        datax = yaml.load_all(fp)
        for data in datax:
            for key, value in data.items():
                dict_res[key] = value
    return dict_res


@click.pass_context
def _set(ctx, key: Key, value):
    if isinstance(value, bool):
        value = str(value).lower()
    ctx.obj[key.envvar[0]] = value


@click.pass_context
def _get(ctx, key: Key, value=None, default="", required=True, allow_interactive=True):
    if isinstance(value, bool):
        value = str(value).lower()

    name = key.envvar[0]
    # if ctx.obj has the key, return it
    if name in ctx.obj:
        logging.trace(f"Found {name} in context object.")  # type: ignore
        return ctx.obj[name]
    # check envvar
    if not value:
        for env_var in key.envvar:
            if env_var in os.environ:
                logging.trace(f"Found {name} in environment variables: {env_var}")  # type: ignore
                value = os.environ[env_var]
                break
    if not value:
        if default:
            logging.debug(f"Using default value for {name}: {default}")
            value = default
    if not value:
        if utilz.is_truthy(_get(Key.GBL_INTERACTIVE, False)) and allow_interactive:
            if sys.stdin.isatty():
                if key.envvar[0].endswith("PASSWORD"):
                    value = click.prompt(
                        f"Please enter the value for {name}",
                        type=str,
                        hide_input=True,
                        default="",
                    )
                else:
                    value = click.prompt(
                        f"Please enter the value for {name}",
                        default=default,
                        type=str,
                        show_default=True,
                    )
                _set(key, value)
                return value
            else:
                die(
                    f"Cannot prompt for {name} as stdin is not a tty. Please set it via environment variable or command line argument."
                )
        elif default is not None:
            logging.debug(f"Using default value for {name}: {default}")
            value = default
    if not value:
        if required:
            die(
                f"No value found for {name} in context object, arg, environment variables or prompt"
            )
        else:
            logging.debug(f"No value found for {name}, returning empty string")
            return ""
    logging.debug(f"Setting {name}...")
    _set(key, value)
    return value


@bundleutils.command()
@click.pass_context
def help_pages(ctx):
    """
    Show all help pages by running 'bundleutils --help' at the global level and each sub command.
    """
    click.echo(ctx.parent.get_help())
    # get all sub commands in alphabetical order
    commands = sorted(bundleutils.commands.keys())

    for key in commands:
        command = bundleutils.commands[key]
        click.echo("-" * 120)
        click.echo(
            command.get_help(ctx.parent).replace(
                "Usage: bundleutils", f"Usage: bundleutils {command.name}"
            )
        )


# @option_for(Key.CI_MAX_START_TIME, default=120, type=int)
#     max_start_time = _get(Key.CI_MAX_START_TIME, max_start_time)


@bundleutils.command()
@option_for(Key.CI_SERVER_HOME, default=os.path.join("target", "ci_server_home"))
@option_for(Key.URL)
@option_for(Key.CI_TYPE)
@option_for(Key.CI_VERSION)
@option_for(Key.CI_SETUP_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.CI_BUNDLE_TEMPLATE, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.CI_FORCE, default="False", type=click.BOOL)
@click.pass_context
def ci_setup(
    ctx, ci_server_home, url, ci_type, ci_version, source_dir, ci_bundle_template, force
):
    """
    Download CloudBees WAR file, and setup the starter bundle.

    \b
    Env vars:
        BUNDLEUTILS_CB_DOCKER_IMAGE_{CI_TYPE}: Docker image for the CI_TYPE (MM, OC)
        BUNDLEUTILS_CB_WAR_DOWNLOAD_URL_{CI_TYPE}: WAR download URL for the CI_TYPE (CM, OC_TRADITIONAL)
        BUNDLEUTILS_SKOPEO_COPY_OPTS: options to pass to skopeo copy command

    \b
        NOTE:
        - All occurences of BUNDLEUTILS_CI_VERSION in the env var value will be replaced.
        - If the value does not include a tag, the CI_VERSION will be appended to it.

    \b
        e.g. Use either...
            BUNDLEUTILS_CB_DOCKER_IMAGE_MM=my-registry/cloudbees-core-mm:BUNDLEUTILS_CI_VERSION
            BUNDLEUTILS_CB_DOCKER_IMAGE_MM=my-registry/cloudbees-core-mm

    """

    ci_server_home = _get(Key.CI_SERVER_HOME, ci_server_home)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    ci_type = _deduce_type(ci_type)
    ci_version = _deduce_version(ci_version)
    if not source_dir:
        passed_dirs = {}
        passed_dirs[Key.CI_SETUP_SOURCE_DIR] = source_dir
        _add_default_dirs_if_necessary(url, ci_version, passed_dirs)
        source_dir = str(_get(Key.CI_SETUP_SOURCE_DIR))
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    ci_bundle_template = _get(
        Key.CI_BUNDLE_TEMPLATE, ci_bundle_template, required=False
    )
    force = utilz.is_truthy(_get(Key.CI_FORCE, force))

    # parse the source directory bundle.yaml file and copy the files under the plugins and catalog keys to the target_jenkins_home_casc_startup_bundle directory
    bundle_yaml = os.path.join(source_dir, "bundle.yaml")
    plugin_files = [bundle_yaml]
    with open(bundle_yaml, "r", encoding="utf-8") as file:
        bundle_yaml = yaml.load(file)
        for key in ["plugins", "catalog"]:
            # list paths to all entries under bundle_yaml.plugins
            if key in bundle_yaml and isinstance(bundle_yaml[key], list):
                for plugin_file in bundle_yaml[key]:
                    plugin_files.append(os.path.join(source_dir, plugin_file))
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.get_war()
    jenkins_manager.create_startup_bundle(plugin_files, ci_bundle_template)
    _update_bundle(jenkins_manager.target_jenkins_home_casc_startup_bundle)


@bundleutils.command()
@option_for(Key.MERGE_CONFIG, type=click.Path(file_okay=True, dir_okay=False))
@option_for(
    Key.MERGE_FILES, type=click.Path(file_okay=True, dir_okay=False), multiple=True
)
@option_for(Key.MERGE_OUTDIR, type=click.Path(file_okay=True, dir_okay=False))
@click.pass_context
def merge_yamls(ctx, config, files, outfile=None):
    """
    Used for merging YAML files of the same type (jcasc, plugins, items, rbac, etc).

    \b
    The merging strategy is defined in a merge-config file. The default contents are shown on execution.
    """

    merge_configs = None
    if config:
        if not os.path.exists(config):
            die(f"Config file '{config}' does not exist")
        else:
            logging.debug(f"Using config file: {config}")
            merge_configs = yaml2dict(config)

    merger = YAMLMerger(merge_configs)
    # warn if less than two files are provided
    if len(files) < 1:
        die(f"Please provide at least one file to merge")
    if len(files) < 2:
        logging.warning(
            f"Merging only makes sense with two files. Returning the first file."
        )
    # merge the files sequentially using the last result as the base
    output = merger.merge_yaml_files(files)
    if not outfile:
        yaml.dump(output, sys.stdout)
    else:
        with open(outfile, "w", encoding="utf-8") as f:
            yaml.dump(output, f)


def _collect_parents(current_bundle, bundles):
    # get the optional parent key from the bundle.yaml
    bundle_yaml = os.path.join(current_bundle, "bundle.yaml")
    if not os.path.exists(bundle_yaml):
        die(f"Bundle file '{bundle_yaml}' does not exist")
    with open(bundle_yaml, "r", encoding="utf-8") as file:
        bundle_yaml = yaml.load(file)
        if "parent" in bundle_yaml:
            parent = bundle_yaml["parent"]
            if parent in bundles:
                die(f"Bundle '{parent}' cannot be a parent of itself")
            parent_dir = os.path.join(os.path.dirname(current_bundle), parent)
            if not os.path.exists(parent_dir):
                die(f"Parent bundle '{parent}' does not exist")
            bundles.insert(0, parent_dir)
            return _collect_parents(parent_dir, bundles)
    return bundles


def _merge_bundles(bundles, use_parent, outdir, config, api_version=None):
    merge_configs = None
    if config:
        if not os.path.exists(config):
            die(f"Config file '{config}' does not exist")
        else:
            logging.debug(f"Using config file: {config}")
            merge_configs = yaml2dict(config)

    # handle parents if necessary
    if use_parent:
        if len(bundles) != 1:
            die(f"Please provide only one bundle when using the --use-parent option")
        new_bundles = _collect_parents(bundles[0], [])
        new_bundles.append(bundles[0])
        logging.info(f"Using parent bundles: {new_bundles}")
        bundles = new_bundles

    merger = YAMLMerger(merge_configs)  # Merge lists of dicts by 'name' field
    # ensure at least two files are provided
    if len(bundles) < 1:
        die(f"Please provide at least one bundle to merge")

    # ensure the outdir and a bundle.yaml exist
    if outdir:
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        out_bundle_yaml = os.path.join(outdir, "bundle.yaml")
        last_bundle_yaml = os.path.join(bundles[-1], "bundle.yaml")
        if not api_version:
            if os.path.exists(last_bundle_yaml):
                # get the apiVersion and kind from the last bundle.yaml
                last_bundle_yaml_dict = yaml2dict(last_bundle_yaml)
                if "apiVersion" in last_bundle_yaml_dict:
                    api_version = last_bundle_yaml_dict["apiVersion"]
                else:
                    logging.warning(
                        f"Bundle file '{last_bundle_yaml}' does not contain an apiVersion. Using default apiVersion: {default_bundle_api_version}"
                    )
                    api_version = default_bundle_api_version
            else:
                logging.debug(
                    f"Bundle file '{last_bundle_yaml}' does not exist. Using default apiVersion: {api_version}"
                )
                api_version = default_bundle_api_version

        with open(out_bundle_yaml, "w", encoding="utf-8") as f:
            logging.info(f"Writing bundle.yaml to {out_bundle_yaml}")
            f.write(f"apiVersion: {api_version}\n")
            f.write(f"id: ''\n")
            f.write(f"description: ''\n")
            f.write(f"version: ''\n")

    # merge the sections
    for section, section_file in bundle_yaml_keys.items():
        output = {}
        section_files = []
        for bundle in bundles:
            section_files.extend(_get_files_for_key(bundle, section))
        if not section_files:
            logging.info(f"No files found for section: {section}")
            continue
        else:
            logging.info(f"Found files for section: {section}")
        # merge the files sequentially using the last result as the base
        output = merger.merge_yaml_files(section_files)
        # special case for plugins, sort the plugins.yaml plugins key by id
        if section == "plugins" and isinstance(output, dict):
            output["plugins"] = sorted(output["plugins"], key=lambda x: x["id"])
        if not outdir:
            print(f"# {section}.yaml")
            yaml.dump(output, sys.stdout)
        else:
            out_section_yaml = os.path.join(outdir, section_file)
            with open(out_section_yaml, "w", encoding="utf-8") as f:
                logging.info(f"Writing section: {section} to {out_section_yaml}")
                yaml.dump(output, f)
            _update_bundle(outdir)


@bundleutils.command()
@option_for(Key.URL)
@option_for(Key.STRICT, default="False", type=click.BOOL)
@option_for(Key.MERGE_CONFIG, type=click.Path(file_okay=True, dir_okay=False))
@option_for(
    Key.MERGE_BUNDLES,
    multiple=True,
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
)
@option_for(Key.MERGE_USE_PARENT, default="False", type=click.BOOL)
@option_for(Key.MERGE_OUTDIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.MERGE_API_VERSION)
@click.pass_context
def merge_bundles(ctx, url, strict, config, bundles, use_parent, outdir, api_version):
    """
    Used for merging bundles. Given a list of bundles, merge them into a single bundle.

    \b
    The merging strategy is defined in a merge config file similar to the merge command.
    The api_version is taken from either (in order):
    - the api_version parameter
    - the last bundle.yaml file in the list of bundles if available
    - the api version of the bundle in BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR
    - the default api_version

    \b
    Given at least two bundles, it will:
    - for each section of the bundle.yaml (plugins, catalog, items, etc)
    - collect all the referenced files in order of the bundles
    - merge them together
    - write the result to the outdir or stdout if not provided
    - update the outdir/bundle.yaml with the new references
    """
    url = _get(Key.URL, url, required=False)
    strict = utilz.is_truthy(_get(Key.STRICT, strict))
    config = _get(Key.MERGE_CONFIG, config, required=False)
    bundles = _get(Key.MERGE_BUNDLES, bundles)
    use_parent = utilz.is_truthy(_get(Key.MERGE_USE_PARENT, use_parent))
    outdir = _get(Key.MERGE_OUTDIR, outdir, required=False)
    api_version = _get(Key.MERGE_API_VERSION, api_version, required=False)

    if isinstance(bundles, str):
        bundles = bundles.split()

    _merge_bundles(bundles, use_parent, outdir, config, api_version)


def announce(string):
    logging.info(f"Announcing...\n{'*' * 80}\n{string}\n{'*' * 80}")


@bundleutils.command()
@option_for(Key.CI_SERVER_HOME, default=os.path.join("target", "ci_server_home"))
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.URL)
@option_for(Key.CI_TYPE)
@option_for(Key.CI_VERSION)
@option_for(Key.VALIDATE_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.VALIDATE_IGNORE_WARNINGS, default="False", type=click.BOOL)
@option_for(
    Key.VALIDATE_EXTERNAL_RBAC,
    type=click.Path(file_okay=True, dir_okay=False, exists=True),
    required=False,
)
@click.pass_context
def ci_validate(
    ctx,
    ci_server_home,
    config_key,
    url,
    ci_version,
    ci_type,
    source_dir,
    ignore_warnings,
    external_rbac,
):
    """Validate bundle against controller started with ci-start."""
    ci_server_home = _get(Key.CI_SERVER_HOME, ci_server_home)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    ci_type = _deduce_type(ci_type)
    ci_version = _deduce_version(ci_version)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    # overwrite the URL in the context object because we are using the test-server
    source_dir = _get_source_dir(url, source_dir)
    _set(Key.URL, server_url)
    logging.debug(
        f"Server URL: {server_url}, Username: {username}, Password: {password}"
    )
    _validate(
        config_key,
        server_url,
        username,
        password,
        source_dir,
        ignore_warnings,
        external_rbac,
    )


def _get_plugins_from_server(server_url, username, password):
    plugin_json_url = utilz.join_url(server_url, plugin_json_url_path)
    response_text = call_jenkins_api(plugin_json_url, username, password)
    return response_text


@bundleutils.command()
@option_for(Key.CI_SERVER_HOME, default=os.path.join("target", "ci_server_home"))
@option_for(Key.URL)
@option_for(Key.CI_TYPE)
@option_for(Key.CI_VERSION)
@option_for(Key.CI_SETUP_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.SANITIZE_PLUGINS_PIN_PLUGINS, default="False", type=click.BOOL)
@option_for(Key.SANITIZE_PLUGINS_CUSTOM_URL)
@click.pass_context
def ci_sanitize_plugins(
    ctx, ci_server_home, url, ci_version, ci_type, source_dir, pin_plugins, custom_url
):
    """Sanitizes plugins (needs ci-start)."""
    ci_server_home = _get(Key.CI_SERVER_HOME, ci_server_home)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    ci_type = _deduce_type(ci_type)
    ci_version = _deduce_version(ci_version)
    passed_dirs = {}
    passed_dirs[Key.CI_SETUP_SOURCE_DIR] = source_dir
    _add_default_dirs_if_necessary(url, ci_version, passed_dirs)
    source_dir = str(_get(Key.CI_SETUP_SOURCE_DIR))
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")

    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)

    server_url, username, password = jenkins_manager.get_server_details()
    logging.debug(
        f"Server URL: {server_url}, Username: {username}, Password: {password}"
    )

    # read the plugins.yaml file from the source directory
    plugins_file = os.path.join(source_dir, "plugins.yaml")
    if not os.path.exists(plugins_file):
        die(f"Plugins file '{plugins_file}' does not exist")
    with open(plugins_file, "r", encoding="utf-8") as f:
        plugins_data = yaml.load(f)  # Load the existing data

    envelope_json = jenkins_manager.get_envelope_json()
    envelope_json = json.loads(envelope_json)

    response_text = _get_plugins_from_server(server_url, username, password)
    data = json.loads(str(response_text))

    installed_plugins = {}
    envelope_plugins = {}
    bootstrap_plugins = {}
    for plugin_id, plugin_info in envelope_json["plugins"].items():
        if plugin_info.get("scope") == "bootstrap":
            logging.debug(f"SANITIZE PLUGINS -> registering bootstrap: {plugin_id}")
            bootstrap_plugins[plugin_id] = plugin_info
        else:
            logging.debug(f"SANITIZE PLUGINS -> registering non-bootstrap: {plugin_id}")
            envelope_plugins[plugin_id] = plugin_info

    for installed_plugin in data["plugins"]:
        installed_plugins[installed_plugin["shortName"]] = installed_plugin

    # Check if 'plugins' key exists and it's a list
    if "plugins" in plugins_data and isinstance(plugins_data["plugins"], list):
        updated_plugins = []
        for plugin in plugins_data["plugins"]:
            if plugin["id"] in envelope_plugins.keys():
                logging.info(f"SANITIZE PLUGINS -> ignoring bundled: {plugin['id']}")
                updated_plugins.append(plugin)
            elif plugin["id"] in bootstrap_plugins.keys():
                logging.info(f"SANITIZE PLUGINS -> removing bootstrap: {plugin['id']}")
            else:
                if custom_url:
                    # remove the version from the plugin
                    plugin.pop("version", None)
                    plugin["url"] = (
                        custom_url.replace("PNAME", plugin["id"])
                        .replace("PVERSION", installed_plugins[plugin["id"]]["version"])
                        .strip()
                    )
                    logging.info(
                        f"SANITIZE PLUGINS -> adding URL to: {plugin['id']} ({plugin['url']})"
                    )
                    updated_plugins.append(plugin)
                elif pin_plugins:
                    if plugin["id"] in installed_plugins:
                        # remove the url from the plugin
                        plugin.pop("url", None)
                        plugin["version"] = installed_plugins[plugin["id"]]["version"]
                        logging.info(
                            f"SANITIZE PLUGINS -> adding version to : {plugin['id']} ({plugin['version']})"
                        )
                        updated_plugins.append(plugin)
                    else:
                        logging.warning(
                            f"SANITIZE PLUGINS -> no version found for: {plugin['id']}"
                        )
                else:
                    logging.info(f"SANITIZE PLUGINS -> not pinning: {plugin['id']}")
                    updated_plugins.append(plugin)
        plugins_data["plugins"] = updated_plugins
    with open(plugins_file, "w", encoding="utf-8") as f:
        yaml.dump(plugins_data, f)  # Write the updated data back to the file
    _update_bundle(source_dir)


@bundleutils.command()
@option_for(Key.CI_SERVER_HOME, default=os.path.join("target", "ci_server_home"))
@option_for(Key.URL)
@option_for(Key.CI_TYPE)
@option_for(Key.CI_VERSION)
@option_for(Key.CI_MAX_START_TIME, default=120, type=click.INT)
@click.pass_context
def ci_start(ctx, ci_server_home, url, ci_version, ci_type, ci_max_start_time):
    """Start CloudBees Server"""
    ci_server_home = _get(Key.CI_SERVER_HOME, ci_server_home)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    ci_type = _deduce_type(ci_type)
    ci_version = _deduce_version(ci_version)
    ci_max_start_time = _get(Key.CI_MAX_START_TIME, ci_max_start_time)

    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.start_server(ci_max_start_time)


@bundleutils.command()
@click.pass_context
@option_for(Key.CI_SERVER_HOME, default=os.path.join("target", "ci_server_home"))
@option_for(Key.URL)
@option_for(Key.CI_TYPE)
@option_for(Key.CI_VERSION)
def ci_stop(ctx, ci_server_home, url, ci_version, ci_type):
    """Stop CloudBees Server"""
    ci_server_home = _get(Key.CI_SERVER_HOME, ci_server_home)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    ci_type = _deduce_type(ci_type)
    ci_version = _deduce_version(ci_version)

    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.stop_server()


@bundleutils.command()
@click.option(
    "-s",
    "--sources",
    multiple=True,
    type=click.Path(file_okay=True, dir_okay=True, exists=True),
    help=f"The directories or files to be diffed.",
)
@click.pass_context
def diff(ctx, sources):
    """Diff two YAML directories or files."""
    # set_logging(False)
    diff_detected = False
    src1 = ""
    src2 = ""
    # if src1 is a directory, ensure src2 is also directory
    if sources and len(sources) == 2:
        src1 = sources[0]
        src2 = sources[1]
    else:
        die("Please provide two directories or files.")
    # if src1 is a directory, ensure src2 is also directory
    if os.path.isdir(src1) and os.path.isdir(src2):
        diff_detected = diff_dirs(src1, src2)
    elif os.path.isfile(src1) and os.path.isfile(src2):
        if diff2(src1, src2):
            diff_detected = True
    else:
        die("src1 and src2 must both be either directories or files")
    if diff_detected:
        die("Differences detected")


@contextmanager
def maybe_temp_dir():
    override = os.getenv("BUNDLEUTILS_TEMP_DIR")
    if override:
        yield override
    else:
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir


@bundleutils.command()
@click.option(
    "-m",
    "--config",
    type=click.Path(file_okay=True, dir_okay=False),
    help=f"An optional custom merge config file if needed.",
)
@click.option(
    "-s",
    "--sources",
    multiple=True,
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
    help=f"The bundles to be diffed.",
)
@click.option(
    "-a",
    "--api-version",
    help=f"Optional apiVersion in case bundle does not contain a bundle.yaml. Defaults to {default_bundle_api_version}",
)
@click.pass_context
def diff_merged(ctx, config, sources, api_version):
    """Diff two bundle directories by temporarily merging both before the diff."""
    # set_logging(False)
    diff_detected = False
    # if src1 is a directory, ensure src2 is also directory
    src1 = ""
    src2 = ""
    if sources and len(sources) == 2:
        src1 = sources[0]
        src2 = sources[1]
    else:
        die("Please provide two bundle directories")

    if os.path.isdir(src1) and os.path.isdir(src2):
        with maybe_temp_dir() as temp_dir:
            merged1 = os.path.join(temp_dir, "merged1", "dummy")
            merged2 = os.path.join(temp_dir, "merged2", "dummy")
            _merge_bundles([src1], False, merged1, config, api_version)
            _merge_bundles([src2], False, merged2, config, api_version)
            diff_detected = diff_dirs(merged1, merged2)

    else:
        die("src1 and src2 must both be directories")

    if diff_detected:
        die("Differences detected")


def diff_dirs(src1, src2):
    files1 = os.listdir(src1)
    files2 = os.listdir(src2)
    diff_detected = False
    for file1 in files1:
        if file1 in files2:
            file1_path = os.path.join(src1, file1)
            file2_path = os.path.join(src2, file1)
            if diff2(file1_path, file2_path):
                diff_detected = True
        else:
            logging.warning(f"File {file1} does not exist in {src2}")
            diff_detected = True
    for file2 in files2:
        if file2 not in files1:
            logging.warning(f"File {file2} does not exist in {src1}")
            diff_detected = True
    return diff_detected


def diff2(file1, file2):
    dict1 = yaml2dict(file1)
    dict2 = yaml2dict(file2)
    diff = DeepDiff(dict1, dict2, ignore_order=True)
    if diff:
        logging.warning(f"Detected diff between {file1} and {file2}")
        click.echo(json.dumps(json.loads(diff.to_json()), indent=2))
        return True
    else:
        logging.info(f"No diff between {file1} and {file2}")
        return False


def _preflight(url, username, password):
    preflight_checks = {}
    try:
        _get_plugins_from_server(url, username, password)
        preflight_checks["plugins-export"] = "OK"
    except Exception as e:
        preflight_checks["plugins-export"] = str(e)

    try:
        _read_core_casc_export_file(url, username, password)
        preflight_checks["casc-export"] = "OK"
    except Exception as e:
        if str(e).startswith("404"):
            preflight_checks["casc-plugins-installed"] = (
                "NOK? Received a 404 when accessing the casc page. Are the plugins installed?"
            )
        preflight_checks["casc-export"] = str(e)
    for value in preflight_checks.values():
        if value != "OK":
            click.echo(json.dumps(preflight_checks, indent=2))
            die(f"Preflight checks failed.")
    else:
        logging.debug("Preflight checks OK.")


@bundleutils.command()
@option_for(Key.URL, required=True)
@option_for(Key.USERNAME, required=True)
@option_for(Key.PASSWORD, required=True)
@click.pass_context
def preflight(ctx, url, username, password):
    """Preconditions for fetching the CasC export."""
    _preflight(url, username, password)


@bundleutils.command()
@option_for(Key.URL)
@option_for(Key.USERNAME)
@option_for(Key.PASSWORD)
@option_for(Key.API_PATH)
@option_for(
    Key.API_DATA_FILE, type=click.Path(exists=True, dir_okay=False), required=False
)
@option_for(Key.API_OUT_FILE, type=click.Path(dir_okay=False), required=False)
@click.pass_context
def api(ctx, url, username, password, path, data_file, out_file):
    """
    Utility for calling the Jenkins API.
    \b
    e.g. bundleutils api -P /whoAmI/api/json?pretty
    """
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}")
    username = _get(Key.USERNAME, username)
    password = _get(Key.PASSWORD, password)
    path = _get(Key.API_PATH, path)
    data_file = str(_get(Key.API_DATA_FILE, data_file, required=False))
    out_file = str(_get(Key.API_OUT_FILE, out_file, required=False))

    _preflight(url, username, password)
    url_path = utilz.join_url(url, path) if path else url
    response = call_jenkins_api(url_path, username, password, data_file, out_file)
    if response:
        click.echo(response)


@bundleutils.command()
@option_for(Key.URL)
@option_for(Key.USERNAME)
@option_for(Key.PASSWORD)
@click.pass_context
def controllers(ctx, url, username, password):
    """
    Return all online controllers from an operation center.
    """
    url = _get(Key.URL, url)
    ci_type = _deduce_type()
    username = _get(Key.USERNAME, username)
    password = _get(Key.PASSWORD, password)

    _preflight(url, username, password)
    if not ci_type or not ci_type in ["oc", "oc-traditional"]:
        die(f"The url must be an operation center url.")
    controllers_api_url = utilz.join_url(url, controllers_url_path)
    response_text = call_jenkins_api(controllers_api_url, username, password)
    controllers = json.loads(str(response_text))
    controllers = utilz.find_controllers(controllers)
    lines = []
    for controller in controllers:
        controller_endpoint = controller.get("endpoint")
        controller_url = controller.get("url")
        if not controller_endpoint:
            logging.debug(f"Controller endpoint not found for {controller_url}")
            continue
        controller_online = controller.get("online")
        if utilz.is_truthy(controller_online):
            logging.debug(f"Controller '{controller_endpoint}' is online.")
            lines.append(controller_endpoint)
        else:
            logging.debug(f"Controller '{controller_endpoint}' is not online.")
    click.echo("\n".join(lines or []))


@click.pass_context
def _config(ctx, key=""):
    """List evaluated config based on cwd and env file."""
    lines = []
    if key == "NONE":
        return lines
    if key == "ALL":
        key = ""

    # if key disable logging
    if key:
        # if key is not in the context
        # check if the key starts with BUNDLEUTILS_
        if not key.startswith("BUNDLEUTILS_"):
            die(f"Key '{key}' must start with 'BUNDLEUTILS_'")
        # check if the key is in the context object
        if key in ctx.obj.keys():
            lines.append(str(ctx.obj[key]))
        else:
            die(f"Key '{key}' not found in configuration.")
        return lines
    # loop through all config values
    for key, value in sorted(ctx.obj.items()):
        if key.startswith("BUNDLEUTILS_"):
            # if the key is a password, mask it
            if "PASSWORD" in key:
                value = "<REDACTED>"
            lines.append(f"{key}={value}")
    return lines


@bundleutils.command()
def version():
    """Show the app version."""
    try:
        package_name = "bundleutilspkg"
        pkg_metadata = metadata(package_name)
        click.echo(f"{pkg_metadata['Version']}")
    except PackageNotFoundError:
        try:
            click.echo(__version__)
        except AttributeError:
            click.echo("Cannot determine version.")
        click.echo(
            "Package is not installed. Please ensure it's built and installed correctly."
        )


@bundleutils.command()
@option_for(Key.URL, required=True)
def extract_version_from_url(url):
    """Get the instance version from the URL."""
    ci_type, ci_version = utilz.lookup_details_from_url(url)
    click.echo(ci_version)


@bundleutils.command()
@option_for(Key.URL, required=True)
def extract_name_from_url(url):
    """
    Smart extraction of the controller name from the URL.

    \b
    Extracts NAME from the following URL formats:
    - http://a.b.c/NAME/
    - http://a.b.c/NAME
    - https://a.b.c/NAME/
    - https://a.b.c/NAME
    - http://NAME.b.c/
    - http://NAME.b.c
    - https://NAME.b.c/
    - https://NAME.b.c
    """
    name = utilz.extract_name_from_url(url)
    click.echo(name)


@bundleutils.command()
@option_for(Key.EXTRACT_STRING, required=True)
@option_for(Key.EXTRACT_PATTERN, default=default_bundle_detection_pattern)
@click.pass_context
def extract_from_pattern(ctx, string, pattern):
    r"""
    Extract the controller name from a string using a regex pattern.
    This command is useful for extracting controller name from a feature branch name or similar strings.

    \b
    e.g.

    - Full string.
    Pattern: ^([a-z0-9\-]+)$

    - Prefix: main-, Suffix: -drift.
    Pattern: ^main-([a-z0-9\-]+)-drift$

    - Prefix: feature/testing-, no suffix.
    Pattern: ^feature/testing-([a-z0-9\-]+)$

    - Prefix: testing-, no suffix.
    Pattern: ^testing-([a-z0-9\-]+)$

    - Prefix: feature/JIRA-1234/, Suffix: optional __something.
    Pattern: ^feature/[A-Z]+-\d+/([a-z0-9\-]+)(?:__[a-z0-9\-]+)*$
    """
    # return the first match of the pattern in the string
    match = re.search(pattern, string)
    if match:
        # if the match is a group, return the first group
        if match.groups():
            click.echo(match.group(1))
        else:
            click.echo(match.group(0))
    else:
        die(f"No match found for pattern '{pattern}' in string '{string}'")


@bundleutils.command()
@option_for(Key.SHELL, type=click.Choice(["bash", "fish", "zsh"]), required=True)
@click.pass_context
def completion(ctx, shell):
    """Print the shell completion script"""
    click.echo("Run either of the following commands to enable completion:")
    click.echo(
        f'  1. eval "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})"'
    )
    click.echo(
        f'  2. echo "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})" > {script_name}-complete.{shell}'
    )
    click.echo(f"     source {script_name}-complete.{shell}")


@bundleutils.command()
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.OC_URL, required=True)
@option_for(Key.URL, required=True)
@option_for(Key.USERNAME, required=True)
@option_for(Key.PASSWORD, required=True)
@option_for(
    Key.VALIDATE_SOURCE_DIR,
    type=click.Path(file_okay=False, dir_okay=True, exists=True),
)
@option_for(Key.VALIDATE_IGNORE_WARNINGS, default="False", type=click.BOOL)
@option_for(
    Key.VALIDATE_EXTERNAL_RBAC,
    type=click.Path(file_okay=True, dir_okay=False, exists=True),
    required=False,
)
@click.pass_context
def validate_effective(
    ctx,
    config_key,
    oc_url,
    url,
    username,
    password,
    source_dir,
    ignore_warnings,
    external_rbac,
):
    """
    Generate effective bundle from OC, then validate effective bundle against URL.

    \b
    This command will:
    - Zip all bundles from the source directory parent
    - Post the zip to the OC to get the effective bundle
    - Validate the effective bundle against the URL
    """
    oc_url = _get(Key.OC_URL, oc_url, required=True)
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}")
    username = _get(Key.USERNAME, username)
    password = _get(Key.PASSWORD, password)
    source_dir = _get_source_dir(url, source_dir)

    # get full path to the source directory
    source_dir = os.path.abspath(source_dir)
    source_dir_base = os.path.basename(source_dir)
    source_dir_parent = os.path.dirname(source_dir)
    source_dir_parent_base = os.path.basename(source_dir_parent)
    source_dir_parent_parent = os.path.dirname(source_dir_parent)
    all_bundles = _find_bundles(source_dir_parent)
    logging.debug(
        f"Bundles {all_bundles} found in {source_dir_parent} from {source_dir}"
    )
    # zip all bundles so that the zip includes source_dir_parent/bundle_name
    temp_dir = os.path.join(
        os.getcwd(), "target", "validate_effective", source_dir_base
    )
    os.makedirs(temp_dir, exist_ok=True)
    logging.debug(f"Temporary directory created at {temp_dir}")
    remove_files_from_dir(temp_dir, 2)
    zip_file_path = os.path.join(temp_dir, "all-bundles.zip")
    # start path is the source_dir_parent
    with zipfile.ZipFile(zip_file_path, "w") as zipf:
        # add the source_dir_parent/bundle_dir to the zip file
        for root, _, files in os.walk(source_dir_parent):
            for file in files:
                file_path = os.path.join(root, file)
                # skip if the files parent is not in all_bundles
                if not any(bundle_dir in root for bundle_dir in all_bundles):
                    continue
                # add the file to the zip file with the relative path
                relative_path = os.path.relpath(file_path, source_dir_parent_parent)
                zipf.write(file_path, relative_path)
    logging.info(f"Zipped all bundles to {zip_file_path}")
    # list the files in the zip file
    with zipfile.ZipFile(zip_file_path, "r") as zipf:
        logging.debug("Files in the zip:")
        for file in zipf.namelist():
            logging.debug(f" - {file}")
    # create a temporary directory to store the effective bundle
    effective_bundle_dir_path = os.path.join(
        temp_dir, f"effective-bundle-{source_dir_base}"
    )
    effective_bundle_zip_path = f"{effective_bundle_dir_path}.zip"
    effective_bundle_url_path = (
        f"{get_effective_bundle_path}{source_dir_parent_base}/{source_dir_base}"
    )
    try:
        logging.info(
            f"Requesting effective bundle from OC at {oc_url} with path {effective_bundle_url_path}"
        )
        call_jenkins_api(
            utilz.join_url(oc_url, effective_bundle_url_path),
            username,
            password,
            data_file=zip_file_path,
            out_file=effective_bundle_zip_path,
        )
        logging.info(f"Effective bundle zip created at {effective_bundle_zip_path}")
        # now unzip the effective bundle
        with zipfile.ZipFile(effective_bundle_zip_path, "r") as zipf:
            zipf.extractall(effective_bundle_dir_path)
        logging.info(f"Effective bundle extracted to {effective_bundle_dir_path}")
        # Now run validate on the effective bundle as normal
        _validate(
            config_key,
            url,
            username,
            password,
            effective_bundle_dir_path,
            ignore_warnings,
            external_rbac,
        )
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            die(
                f"OC URL {oc_url} does not support effective bundle generation. Please check the URL."
            )
        else:
            die(f"Failed to get effective bundle from OC: {e}")


@bundleutils.command()
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.URL)
@option_for(Key.USERNAME)
@option_for(Key.PASSWORD)
@option_for(Key.VALIDATE_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.VALIDATE_IGNORE_WARNINGS, default="False", type=click.BOOL)
@option_for(
    Key.VALIDATE_EXTERNAL_RBAC,
    type=click.Path(file_okay=True, dir_okay=False, exists=True),
    required=False,
)
@click.pass_context
def validate(
    ctx, config_key, url, username, password, source_dir, ignore_warnings, external_rbac
):
    """Validate bundle in source dir against URL."""

    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}")
    _validate(
        config_key, url, username, password, source_dir, ignore_warnings, external_rbac
    )


def _get_source_dir(url, source_dir):
    if not source_dir:
        ci_version = _deduce_version()
        passed_dirs = {}
        passed_dirs[Key.VALIDATE_SOURCE_DIR] = source_dir
        _add_default_dirs_if_necessary(url, ci_version, passed_dirs)
        source_dir = str(_get(Key.VALIDATE_SOURCE_DIR))
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    return source_dir


def _validate(
    config_key, url, username, password, source_dir, ignore_warnings, external_rbac
):
    if not config_key in ["ALL", "NONE"]:
        logging.getLogger().setLevel(logging.WARNING)
    url = str(_get(Key.URL, url))
    username = _get(Key.USERNAME, username)
    password = _get(Key.PASSWORD, password)

    source_dir = _get_source_dir(url, source_dir)
    external_rbac = _get(Key.VALIDATE_EXTERNAL_RBAC, external_rbac, required=False)
    ignore_warnings = utilz.is_truthy(
        _get(Key.VALIDATE_IGNORE_WARNINGS, ignore_warnings)
    )

    if external_rbac:
        if not os.path.exists(external_rbac):
            die(f"RBAC configuration file not found in {external_rbac}")
        logging.info(f"Using RBAC from {external_rbac}")

    # if the url does end with /casc-bundle-mgnt/casc-bundle-validate, append it
    if validate_url_path not in url:
        url = utilz.join_url(url, validate_url_path)

    if _print_config(config_key):
        return

    logging.info(f"Validating bundle in {source_dir} against {url}")
    # fetch the YAML from the URL
    headers = {"Content-Type": "application/zip"}
    if username and password:
        headers["Authorization"] = "Basic " + base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("utf-8")

    # create a temporary directory to store the bundle
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.debug(
            f"Copying bundle files recursively to {temp_dir} keeping structure"
        )
        for root, dirs, files in os.walk(source_dir):
            # create the same directory structure in the temp_dir
            relative_path = os.path.relpath(root, source_dir)
            target_dir = os.path.join(temp_dir, relative_path)
            os.makedirs(target_dir, exist_ok=True)
            for file in files:
                file_path = os.path.join(root, file)
                shutil.copy2(file_path, target_dir)
        if external_rbac:
            logging.info(
                f"Copying external RBAC file {external_rbac} to {temp_dir}. Will need to update the bundle.yaml."
            )
            shutil.copy2(
                external_rbac,
                os.path.join(temp_dir),
            )
            _update_bundle(temp_dir)
        # zip and post the YAML to the URL
        with zipfile.ZipFile("bundle.zip", "w") as zip_ref:
            # add the source_dir_parent/bundle_dir to the zip file
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # add the file to the zip file with the relative path
                    relative_path = os.path.relpath(file_path, temp_dir)
                    zip_ref.write(file_path, relative_path)
        # list the files in the zip file
        with zipfile.ZipFile("bundle.zip", "r") as zip_ref:
            logging.debug("Files in the zip:")
            for file in zip_ref.namelist():
                logging.debug(f" - {file}")
        with open("bundle.zip", "rb") as f:
            # post as binary file
            response = requests.post(url, headers=headers, data=f)
    response.raise_for_status()
    # delete the zip file
    os.remove("bundle.zip")
    # print the response as pretty JSON
    response_json = {}
    try:
        response_json = response.json()
    except json.decoder.JSONDecodeError:
        die(f"Failed to decode JSON from response: {response.text}")
    click.echo(json.dumps(response_json, indent=2))
    # Filter out non-info messages
    if "validation-messages" not in response_json:
        logging.warning(
            "No validation messages found in response. Is this an old CI version?"
        )
        # check if the valid key exists and is True
        if "valid" not in response_json or not response_json["valid"]:
            die("Validation failed. See response for details.")
    else:
        non_info_messages = [
            message
            for message in response_json["validation-messages"]
            if not message.startswith("INFO -")
        ]
        if non_info_messages:
            # if non info messages only include warnings...
            if all("WARNING -" in message for message in non_info_messages):
                if not ignore_warnings:
                    die("Validation failed with warnings")
                else:
                    logging.warning(
                        "Validation failed with warnings. Ignoring due to --ignore-warnings flag"
                    )
            else:
                die("Validation failed with errors or critical messages")


def _convert_strategies_to_enums(
    plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy
):
    logging.debug(f"Converting strategies to enums...")
    lines = []
    try:
        plugins_json_list_strategy = PluginJsonListStrategy[plugins_json_list_strategy]
    except KeyError:
        lines.append(
            f"{Key.PLUGINS_JSON_LIST_STRATEGY.envvar[0]}: {plugins_json_list_strategy} (out of {get_name_from_enum(PluginJsonListStrategy)})"
        )
    try:
        plugins_json_merge_strategy = PluginJsonMergeStrategy[
            plugins_json_merge_strategy
        ]
    except KeyError:
        lines.append(
            f"{Key.PLUGINS_JSON_MERGE_STRATEGY.envvar[0]}: {plugins_json_merge_strategy} (out of {get_name_from_enum(PluginJsonMergeStrategy)})"
        )
    try:
        catalog_warnings_strategy = PluginCatalogWarningsStrategy[
            catalog_warnings_strategy
        ]
    except KeyError:
        lines.append(
            f"{Key.PLUGINS_CATALOG_WARNINGS_STRATEGY.envvar[0]}: {catalog_warnings_strategy} (out of {get_name_from_enum(PluginCatalogWarningsStrategy)})"
        )
    if lines:
        lines_str = "\n".join(lines)
        die(
            f"""
            Invalid strategies provided:
            {lines_str}
            Please use one of the valid strategies.
            """
        )
    return (
        plugins_json_list_strategy,
        plugins_json_merge_strategy,
        catalog_warnings_strategy,
    )


def _print_config(config_key):
    """Print the configuration for the given config key."""
    lines = _config(config_key)
    if lines:
        logging.info("Evaluated configuration:")
        click.echo("\n".join(lines or []))
        return True
    return False


@bundleutils.command()
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.FETCH_LOCAL_PATH, type=click.Path(file_okay=True, dir_okay=False))
@option_for(Key.URL)
@option_for(Key.USERNAME)
@option_for(Key.PASSWORD)
@option_for(Key.FETCH_TARGET_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.FETCH_IGNORE_ITEMS, default="False", type=click.BOOL)
@option_for(Key.FETCH_KEYS_TO_SCALARS, default=default_keys_to_scalars)
@option_for(Key.PLUGINS_USE_CAP, default="False", type=click.BOOL)
@option_for(Key.PLUGINS_JSON_LIST_STRATEGY, default=PluginJsonListStrategy.AUTO.name)
@option_for(
    Key.PLUGINS_JSON_MERGE_STRATEGY,
    default=PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED.name,
)
@option_for(
    Key.PLUGINS_CATALOG_WARNINGS_STRATEGY,
    default=PluginCatalogWarningsStrategy.FAIL.name,
)
@click.pass_context
def fetch(
    ctx,
    config_key,
    path,
    url,
    username,
    password,
    target_dir,
    ignore_items,
    keys_to_scalars,
    use_cap,
    plugins_json_list_strategy,
    plugins_json_merge_strategy,
    catalog_warnings_strategy,
):
    """Fetch YAML documents from a URL."""
    if not config_key in ["ALL", "NONE"]:
        logging.getLogger().setLevel(logging.WARNING)

    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False)
    if url:
        username = _get(Key.USERNAME, username)
        password = _get(Key.PASSWORD, password)
    else:
        logging.warning("No URL provided. Checking for a local path.")
        path = _get(Key.FETCH_LOCAL_PATH, path)

    if not target_dir:
        ci_version = _deduce_version()
        passed_dirs = {}
        passed_dirs[Key.FETCH_TARGET_DIR] = target_dir
        _add_default_dirs_if_necessary(url, ci_version, passed_dirs)
        target_dir = _get(Key.FETCH_TARGET_DIR)

    ignore_items = utilz.is_truthy(_get(Key.FETCH_IGNORE_ITEMS, ignore_items))
    keys_to_scalars = _get(Key.FETCH_KEYS_TO_SCALARS, keys_to_scalars)
    use_cap = utilz.is_truthy(_get(Key.PLUGINS_USE_CAP, use_cap))
    plugins_json_list_strategy = _get(
        Key.PLUGINS_JSON_LIST_STRATEGY, plugins_json_list_strategy
    )
    plugins_json_merge_strategy = _get(
        Key.PLUGINS_JSON_MERGE_STRATEGY, plugins_json_merge_strategy
    )
    catalog_warnings_strategy = _get(
        Key.PLUGINS_CATALOG_WARNINGS_STRATEGY, catalog_warnings_strategy
    )

    (
        plugins_json_list_strategy,
        plugins_json_merge_strategy,
        catalog_warnings_strategy,
    ) = _convert_strategies_to_enums(
        plugins_json_list_strategy,
        plugins_json_merge_strategy,
        catalog_warnings_strategy,
    )

    if _print_config(config_key):
        return
    if not path:
        _preflight(url, username, password)

    try:
        fetch_yaml_docs(ignore_items, path, url, username, password, target_dir)
    except Exception as e:
        die(f"Failed to fetch and write YAML documents: {e}", e)
    try:
        _update_plugins(
            url,
            username,
            password,
            target_dir,
            plugins_json_list_strategy,
            plugins_json_merge_strategy,
            use_cap,
        )
    except Exception as e:
        die(f"Failed to fetch and update plugin data: {e}", e)
    # TODO remove as soon as the export does not add '^' to variables
    handle_unwanted_escape_characters(target_dir)


def handle_unwanted_escape_characters(target_dir):
    prefix = "ESCAPE CHAR CHECK - SECO-3944: "
    # check in the jenkins.yaml file for the key 'cascItemsConfiguration.variableInterpolationEnabledForAdmin'
    jenkins_yaml = os.path.join(target_dir, "jenkins.yaml")
    if not os.path.exists(jenkins_yaml):
        die(
            f"Jenkins YAML file '{jenkins_yaml}' does not exist (something seriously wrong here)"
        )
    with open(jenkins_yaml, "r", encoding="utf-8") as f:
        jenkins_data = yaml.load(f)
    if (
        "unclassified" in jenkins_data
        and "cascItemsConfiguration" in jenkins_data["unclassified"]
        and "variableInterpolationEnabledForAdmin"
        in jenkins_data["unclassified"]["cascItemsConfiguration"]
    ):
        pattern = r"\^{1,}\$\{"
        search_replace = "${"
        interpolation_enabled = jenkins_data["unclassified"]["cascItemsConfiguration"][
            "variableInterpolationEnabledForAdmin"
        ]
        if interpolation_enabled == "true":
            # replace all instances of multiple '^' followed by with '${' with '^${' in the jenkins.yaml file
            pattern = r"\^{2,}\$\{"
            search_replace = "^${"
        items_yaml = os.path.join(target_dir, "items.yaml")
        if os.path.exists(items_yaml):
            with open(items_yaml, "r", encoding="utf-8") as f:
                items_data = yaml.load(f)
            logging.info(
                f"{prefix}Variable interpolation enabled for admin = {interpolation_enabled}. Replacing '{pattern}' with '{search_replace}' in items.yaml"
            )
            items_data = replace_string_in_dict(
                items_data, pattern, search_replace, prefix
            )
            logging.info(
                f"EQUAL DISPLAY_NAME CHECK: Setting 'displayName' to empty string if necessary..."
            )
            items_data = replace_display_name_if_necessary(items_data)
            with open(items_yaml, "w", encoding="utf-8") as f:
                yaml.dump(items_data, f)


def replace_display_name_if_necessary(data):
    if isinstance(data, dict):
        # if dict has key 'displayName' and 'name' and they are the same, remove the 'displayName' key
        if (
            "displayName" in data
            and "name" in data
            and data["displayName"] == data["name"]
        ):
            logging.debug(
                f"EQUAL DISPLAY_NAME CHECK: Setting 'displayName' to empty string since equal to name: {data['name']}"
            )
            data["displayName"] = ""
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = replace_display_name_if_necessary(value)
            elif isinstance(value, list):
                data[key] = replace_display_name_if_necessary(value)
            data[key] = value
    elif isinstance(data, list):
        for i, value in enumerate(data):
            if isinstance(value, dict):
                data[i] = replace_display_name_if_necessary(value)
            elif isinstance(value, list):
                data[i] = replace_display_name_if_necessary(value)
    return data


def replace_string_in_dict(data, pattern, replacement, prefix=""):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = replace_string_in_dict(value, pattern, replacement, prefix)
            elif isinstance(value, list):
                data[key] = replace_string_in_list(value, pattern, replacement, prefix)
            elif isinstance(value, str):
                match = re.search(pattern, value)
                if match:
                    # if env var BUNDLEUTILS_TRACE is set, print the replacement
                    if logging.getLogger().isEnabledFor(logging.TRACE):  # type: ignore
                        logging.trace(  # type: ignore
                            f"{prefix}Replacing '{pattern}' with '{replacement}' in dict '{value}'"
                        )
                    else:
                        logging.debug(
                            f"{prefix}Replacing '{pattern}' with '{replacement}' in dict (use TRACE for details)"
                        )
                    data[key] = re.sub(pattern, replacement, value)
    return data


def replace_string_in_list(data, pattern, replacement, prefix=""):
    for i, value in enumerate(data):
        if isinstance(value, dict):
            data[i] = replace_string_in_dict(value, pattern, replacement, prefix)
        elif isinstance(value, list):
            data[i] = replace_string_in_list(value, pattern, replacement, prefix)
        elif isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                logging.debug(
                    f"{prefix}Replacing '{pattern}' with '{replacement}' in list '{value}'"
                )
                data[i] = re.sub(pattern, replacement, value)
    return data


def show_diff(title, plugins, col1, col2):
    hline(f"DIFF: {title}")
    for plugin in sorted(plugins):
        if plugin not in col1 and plugin not in col2:
            continue
        # print fixed width columns for the plugin name in each graph
        # in the format plugin_name | < or > or = | plugin_name
        str = ""
        if plugin not in col2:
            logging.trace(f"{plugin:40} < {str:40}")  # type: ignore
        elif plugin not in col1:
            logging.trace(f"{str:40} > {plugin:40}")  # type: ignore
        else:
            logging.trace(f"{plugin:40} | {plugin:40}")  # type: ignore


def hline(text):
    logging.trace("-" * 80)  # type: ignore
    logging.trace(text)  # type: ignore
    logging.trace("-" * 80)  # type: ignore


# graph types
graph_type_all = "all"
graph_type_minus_bootstrap = "minus-bootstrap"
graph_type_minus_deleted_disabled = "minus-deleted-disabled"


@click.pass_context
def _analyze_server_plugins(
    ctx, plugins_from_json, plugins_json_list_strategy, cap, url
):
    logging.info("Plugin Analysis - Analyzing server plugins...")
    # Setup the dependency graphs
    graphs = {}
    graph_types = [
        graph_type_all,
        graph_type_minus_bootstrap,
        graph_type_minus_deleted_disabled,
    ]
    for graph_type in graph_types:
        graphs[graph_type] = {}
        dependency_graph = defaultdict(
            lambda: {"non_optional": [], "optional": [], "entry": {}}
        )
        reverse_dependencies = defaultdict(list)
        graphs[graph_type]["dependency_graph"] = dependency_graph
        graphs[graph_type]["reverse_dependencies"] = reverse_dependencies
        # Build the dependency graph from the json data
        for plugin in plugins_from_json:
            if (
                graph_type
                in [graph_type_minus_bootstrap, graph_type_minus_deleted_disabled]
            ) and plugin.get("bundled", True):
                continue
            if graph_type == graph_type_minus_deleted_disabled and (
                not plugin.get("enabled", True) or plugin.get("deleted", True)
            ):
                continue
            plugin_name = plugin.get("shortName")
            dependency_graph[plugin_name]["entry"] = plugin
            plugin_dependencies = plugin.get("dependencies", [])
            for dependency in plugin_dependencies:
                dep_name = dependency.get("shortName")
                if dependency.get("optional", False):
                    dependency_graph[plugin_name]["optional"].append(dep_name)  # type: ignore
                else:
                    dependency_graph[plugin_name]["non_optional"].append(dep_name)  # type: ignore
                    # Add the parent plugin to the for non-optional dependencies only
                    reverse_dependencies[dep_name].append(plugin_name)
    logging.debug("Plugin Analysis - Finished building dependency graphs")

    # Function to recursively get all non-optional dependencies
    def get_non_optional_dependencies(graph_type, plugin_name, visited=None):
        dependency_graph = graphs[graph_type]["dependency_graph"]
        if visited is None:
            visited = set()
        if plugin_name in visited:
            return set()  # Avoid infinite loops in cyclic graphs
        visited.add(plugin_name)
        non_optional_deps = set(dependency_graph[plugin_name]["non_optional"])
        for dep in dependency_graph[plugin_name]["non_optional"]:
            non_optional_deps.update(
                get_non_optional_dependencies(graph_type, dep, visited)
            )
        return non_optional_deps

    # Function to find root plugins (those NOT listed as dependencies of any other plugin)
    def find_root_plugins(graph_type):
        dependency_graph = graphs[graph_type]["dependency_graph"]
        reverse_dependencies = graphs[graph_type]["reverse_dependencies"]
        all_plugins = set(dependency_graph.keys())
        all_dependencies = set(reverse_dependencies.keys())
        root_plugins = (
            all_plugins - all_dependencies
        )  # Plugins that are not dependencies
        return root_plugins

    # Function to recursively build a dependency tree as a list
    def build_dependency_list(
        graph_type, plugin_name, parent_line=None, output_list=None
    ):
        dependency_graph = graphs[graph_type]["dependency_graph"]
        if parent_line is None:
            parent_line = []
        if output_list is None:
            output_list = []

        # Add this plugin to the parent line
        parent_line = parent_line + [plugin_name]

        for dep in dependency_graph[plugin_name]["non_optional"]:
            if dep in parent_line:  # Cyclical dependency check
                die(f"Cyclic dependency detected: {parent_line} -> {dep}")
            else:
                output_list.append(parent_line + [dep])  # Add the full path as a list
                build_dependency_list(graph_type, dep, parent_line, output_list)

        return output_list

    # Function to render the dependency list with a given separator
    def render_dependency_list(dependency_list, separator=" -> "):
        return [separator.join(path) for path in dependency_list]

    dgall = graphs[graph_type_all]["dependency_graph"]
    for graph_type in graph_types:
        graphs[graph_type]["roots"] = find_root_plugins(graph_type)
        # render the dependency tree for each root plugin
        for plugin in graphs[graph_type]["roots"]:
            logging.trace(f"Dependency tree for root plugin: {plugin}")  # type: ignore
            dependency_list = build_dependency_list(graph_type, plugin)
            for line in render_dependency_list(dependency_list):
                logging.trace(line)  # type: ignore
    for graph_type in graph_types:
        # create a list of all roots and their non-optional dependencies
        result = set()
        for plugin in graphs[graph_type]["roots"]:
            result.add(plugin)
            result.update(get_non_optional_dependencies(graph_type_all, plugin))
        graphs[graph_type]["roots-and-deps"] = result
    dgmbr = graphs[graph_type_minus_bootstrap]["roots"]
    dgmdr = graphs[graph_type_minus_deleted_disabled]["roots"]

    show_diff(
        "Expected root plugins < vs > expected root plugins after deleted/disabled removed (any new roots on the right side are candidates for removal)",
        dgall.keys(),
        dgmbr,
        dgmdr,
    )

    # handle the list strategy
    expected_plugins = []
    if plugins_json_list_strategy == PluginJsonListStrategy.ROOTS:
        expected_plugins = graphs[graph_type_minus_deleted_disabled]["roots"]
    elif plugins_json_list_strategy == PluginJsonListStrategy.ROOTS_AND_DEPS:
        expected_plugins = graphs[graph_type_minus_deleted_disabled]["roots-and-deps"]
    elif plugins_json_list_strategy == PluginJsonListStrategy.ALL:
        expected_plugins = list(dgall.keys())
    else:
        die(
            f"Invalid plugins json list strategy: {plugins_json_list_strategy.name}. Expected one of: {PluginJsonListStrategy.ALL.name}, {PluginJsonListStrategy.ROOTS.name}, {PluginJsonListStrategy.ROOTS_AND_DEPS.name}"
        )

    # handle the removal of CAP plugin dependencies removal
    if cap:
        if plugins_json_list_strategy == PluginJsonListStrategy.ALL:
            logging.info(
                f"{Key.PLUGINS_JSON_LIST_STRATEGY.envvar[0]} option detected with ALL strategy. Ignoring..."
            )
        else:
            logging.info(
                f"{Key.PLUGINS_USE_CAP.envvar[0]} option detected. Removing CAP plugin dependencies..."
            )
            expected_plugins_copy = expected_plugins.copy()
            if not url:
                die("No URL provided for CAP plugin removal")
            ci_server_home = _get(
                Key.CI_SERVER_HOME, os.path.join("target", "ci_server_home")
            )
            ci_type = _deduce_type()
            ci_version = _deduce_version()
            jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
            envelope_json = jenkins_manager.get_envelope_json_from_war()
            envelope_json = json.loads(envelope_json)
            for plugin_id, plugin_info in envelope_json["plugins"].items():
                if plugin_info.get("scope") != "bootstrap":
                    for dep in get_non_optional_dependencies(graph_type_all, plugin_id):
                        if dep in expected_plugins:
                            logging.debug(f"Removing dependency of {plugin_id}: {dep}")
                            expected_plugins.remove(dep)
            show_diff(
                "Expected root plugins < vs > expected root plugins after CAP dependencies removed",
                dgall.keys(),
                expected_plugins_copy,
                expected_plugins,
            )

    logging.info("Plugin Analysis - finished analysis.")

    # Sanity check:
    # reduced_plugins (and all non_optional_dependencies) + all_bootstrap_plugins (and all non_optional_dependencies) should be equal to original_plugins
    logging.debug("Plugin Analysis - Performing sanity check...")
    logging.debug(
        "Plugin Analysis - Expecting expected_plugins + bootstrap_plugins + deleted_plugins (+ their non_optional_dependencies) should be equal to original_plugins"
    )
    all_bootstrap_plugins = (
        graphs[graph_type_all]["dependency_graph"].keys()
        - graphs[graph_type_minus_bootstrap]["dependency_graph"].keys()
    )
    all_deleted_or_inactive_plugins = (
        graphs[graph_type_all]["dependency_graph"].keys()
        - graphs[graph_type_minus_deleted_disabled]["dependency_graph"].keys()
    )
    sanity_check = set()
    for plugin in expected_plugins:
        sanity_check.add(plugin)
        sanity_check.update(get_non_optional_dependencies(graph_type_all, plugin))
    for plugin in all_bootstrap_plugins:
        sanity_check.add(plugin)
        sanity_check.update(get_non_optional_dependencies(graph_type_all, plugin))
    for plugin in all_deleted_or_inactive_plugins:
        sanity_check.add(plugin)
    if sanity_check != graphs[graph_type_all]["dependency_graph"].keys():
        logging.error(
            "Sanity check failed. Reduced plugins and bootstrap plugins do not match original plugins."
        )
        die(
            "Sanity check failed. Reduced plugins and bootstrap plugins do not match original plugins."
        )
    else:
        logging.debug("Plugin Analysis - Sanity check passed.")

    expected_plugins = sorted(expected_plugins)
    return (
        expected_plugins,
        all_bootstrap_plugins,
        all_deleted_or_inactive_plugins,
        graphs,
    )


# Function to find all plugins with `pluginX` in their dependency tree
def plugins_with_plugin_in_tree(graphs, graph_type, target_plugin):
    reverse_dependency_graph = graphs[graph_type]["reverse_dependencies"]
    result = set()
    to_visit = {target_plugin}

    # Traverse the reverse dependency graph
    while to_visit:
        current = to_visit.pop()
        if current in result:
            continue
        result.add(current)
        to_visit.update(
            reverse_dependency_graph[current]
        )  # Add plugins that depend on `current`

    result.discard(target_plugin)  # Exclude the target plugin itself from the result
    return result


def find_plugin_by_id(plugins, plugin_id):
    logging.trace(f"Finding plugin by id: {plugin_id}")  # type: ignore
    for plugin in plugins:
        if plugin.get("id") == plugin_id:
            return plugin
    return None


@bundleutils.command()
@option_for(Key.URL)
@option_for(Key.USERNAME)
@option_for(Key.PASSWORD)
@option_for(Key.FETCH_TARGET_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.FETCH_IGNORE_ITEMS, default="False", type=click.BOOL)
@option_for(Key.PLUGINS_USE_CAP, default="False", type=click.BOOL)
@option_for(Key.PLUGINS_JSON_LIST_STRATEGY, default=PluginJsonListStrategy.AUTO.name)
@option_for(
    Key.PLUGINS_JSON_MERGE_STRATEGY,
    default=PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED.name,
)
@option_for(
    Key.PLUGINS_CATALOG_WARNINGS_STRATEGY,
    default=PluginCatalogWarningsStrategy.FAIL.name,
)
@click.pass_context
def update_plugins(
    ctx,
    url,
    username,
    password,
    target_dir,
    use_cap,
    plugins_json_list_strategy,
    plugins_json_merge_strategy,
    catalog_warnings_strategy,
):
    """Update plugins in the target directory."""
    url = _get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}")
    ci_version = _deduce_version()
    username = _get(Key.USERNAME, username)
    password = _get(Key.PASSWORD, password)

    passed_dirs = {}
    passed_dirs[Key.FETCH_TARGET_DIR] = target_dir
    _add_default_dirs_if_necessary(url, ci_version, passed_dirs)
    target_dir = _get(Key.FETCH_TARGET_DIR)

    use_cap = _get(Key.PLUGINS_USE_CAP, use_cap)
    plugins_json_list_strategy = _get(
        Key.PLUGINS_JSON_LIST_STRATEGY, plugins_json_list_strategy
    )
    plugins_json_merge_strategy = _get(
        Key.PLUGINS_JSON_MERGE_STRATEGY, plugins_json_merge_strategy
    )
    catalog_warnings_strategy = _get(Key.PLUGINS_CATALOG_WARNINGS_STRATEGY)

    (
        plugins_json_list_strategy,
        plugins_json_merge_strategy,
        catalog_warnings_strategy,
    ) = _convert_strategies_to_enums(
        plugins_json_list_strategy,
        plugins_json_merge_strategy,
        catalog_warnings_strategy,
    )

    _preflight(url, username, password)

    try:
        _update_plugins(
            url,
            username,
            password,
            target_dir,
            plugins_json_list_strategy,
            plugins_json_merge_strategy,
            use_cap,
        )
    except Exception as e:
        die(f"Failed to fetch and update plugin data: {e}", e)


@click.pass_context
def _update_plugins(
    ctx,
    url,
    username,
    password,
    target_dir,
    plugins_json_list_strategy,
    plugins_json_merge_strategy,
    use_cap,
):
    # if no plugins_json_list_strategy is provided, determine it based on the apiVersion in the bundle.yaml file
    if plugins_json_list_strategy == PluginJsonListStrategy.AUTO:
        # find the apiVersion from the bundle.yaml file
        bundle_yaml = os.path.join(target_dir, "bundle.yaml")
        if os.path.exists(bundle_yaml):
            with open(bundle_yaml, "r", encoding="utf-8") as f:
                bundle_yaml = yaml.load(f)
                api_version = bundle_yaml.get("apiVersion", "")
                if not api_version:
                    die("No apiVersion found in bundle.yaml file")
                # if either integer or string, convert to string
                if isinstance(api_version, int):
                    api_version = str(api_version)
                if api_version == "1":
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS_AND_DEPS
                    ctx.obj["plugins_json_list_strategy"] = plugins_json_list_strategy
                elif api_version == "2":
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS
                    ctx.obj["plugins_json_list_strategy"] = plugins_json_list_strategy
                else:
                    die(f"Invalid apiVersion found in bundle.yaml file: {api_version}")

    logging.info(
        f"Plugins JSON list strategy: {plugins_json_list_strategy.name} from {get_name_from_enum(PluginJsonListStrategy)}"
    )
    logging.info(
        f"Plugins JSON merge strategy: {plugins_json_merge_strategy.name} from {get_name_from_enum(PluginJsonMergeStrategy)}"
    )

    # load the plugin JSON from the URL or path
    plugin_json_str = None
    if url:
        plugin_json_url = utilz.join_url(url, plugin_json_url_path)
        logging.debug(f"Loading plugin JSON from URL: {plugin_json_url}")
        plugin_json_str = call_jenkins_api(plugin_json_url, username, password)
    else:
        logging.info(
            "No plugin JSON URL provided. Cannot determine if disabled/deleted plugins present in list."
        )
        return
    data = json.loads(str(plugin_json_str))
    plugins_from_json = data.get("plugins", [])
    expected_plugins, all_bootstrap_plugins, all_deleted_or_inactive_plugins, graphs = (
        _analyze_server_plugins(
            plugins_from_json, plugins_json_list_strategy, use_cap, url
        )
    )

    # checking the plugin-catalog.yaml file
    plugin_catalog_plugin_ids_previous = []
    plugin_catalog_plugin_ids = []
    plugin_catalog = os.path.join(target_dir, "plugin-catalog.yaml")
    if os.path.exists(plugin_catalog):
        with open(plugin_catalog, "r", encoding="utf-8") as f:
            catalog_data = yaml.load(f)  # Load the existing data
        logging.info(
            f"Looking for disabled/deleted plugins to remove from plugin-catalog.yaml"
        )
        # Check and remove plugins listed in filtered_plugins from includePlugins
        for configuration in catalog_data.get("configurations", []):
            if "includePlugins" in configuration:
                for plugin_id in list(configuration["includePlugins"]):
                    plugin_catalog_plugin_ids_previous.append(plugin_id)
                    if plugin_id in all_deleted_or_inactive_plugins:
                        if plugins_json_merge_strategy.should_delete:
                            logging.debug(
                                f" -> removing disabled/deleted plugin {plugin_id} according to merge strategy: {plugins_json_merge_strategy.name}"
                            )
                            del configuration["includePlugins"][plugin_id]
                        else:
                            logging.warning(
                                f" -> unexpected plugin {plugin_id} found but not removed according to merge strategy: {plugins_json_merge_strategy.name}"
                            )
                            plugin_catalog_plugin_ids.append(plugin_id)
                    else:
                        plugin_catalog_plugin_ids.append(plugin_id)

        if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
            logging.info(
                f"Skipping writing to plugin-catalog.yaml according to merge strategy: {plugins_json_merge_strategy.name}"
            )
        else:
            with open(plugin_catalog, "w", encoding="utf-8") as file:
                yaml.dump(catalog_data, file)  # Write the updated data back to the file

    # removing from the plugins.yaml file
    plugins_file = os.path.join(target_dir, "plugins.yaml")
    if os.path.exists(plugins_file):
        with open(plugins_file, "r", encoding="utf-8") as f:
            plugins_data = yaml.load(f)  # Load the existing data

        original_plugin_data = plugins_data.copy()
        current_plugins = []
        updated_plugins = []
        # Check if 'plugins' key exists and it's a list
        if "plugins" in plugins_data and isinstance(plugins_data["plugins"], list):
            logging.debug(f"Found 'plugins' key in current plugins.yaml")
            current_plugins = plugins_data["plugins"]

        logging.info(
            f"Looking for disabled/deleted plugins to remove from current plugins.yaml"
        )
        for plugin in current_plugins:
            if plugin["id"] in plugin_catalog_plugin_ids:
                logging.trace(  # type: ignore
                    f" -> skipping plugin {plugin['id']} due to entry in plugin-catalog.yaml"
                )
                updated_plugins.append(plugin)
                continue
            if plugin["id"] in all_bootstrap_plugins:
                if plugins_json_merge_strategy == PluginJsonMergeStrategy.ALL:
                    logging.trace(  # type: ignore
                        f" -> keeping bootstrap plugin {plugin['id']} according to merge strategy: {plugins_json_merge_strategy.name}"
                    )
                    updated_plugins.append(plugin)
                else:
                    logging.trace(f" -> removing bootstrap plugin {plugin['id']}")  # type: ignore
                continue
            if not plugin["id"] in expected_plugins:
                if plugins_json_merge_strategy.skip_pinned:
                    # if plugin map has a url or version, skip it
                    if "url" in plugin:
                        logging.trace(  # type: ignore
                            f" -> skipping plugin {plugin['id']} with pinned url according to merge strategy: {plugins_json_merge_strategy.name}"
                        )
                        updated_plugins.append(plugin)
                    elif "version" in plugin:
                        logging.trace(  # type: ignore
                            f" -> skipping plugin {plugin['id']} with pinned version according to merge strategy: {plugins_json_merge_strategy.name}"
                        )
                        updated_plugins.append(plugin)
                    else:
                        # find the plugins in the reverse_dependencies that are also in the expected_plugins
                        associated_parents = plugins_with_plugin_in_tree(
                            graphs, graph_type_minus_bootstrap, plugin["id"]
                        )
                        expected_parents = ", ".join(
                            associated_parents.intersection(expected_plugins)
                        )
                        logging.trace(  # type: ignore
                            f" -> removing non-pinned plugin {plugin['id']} (parents: {expected_parents}) according to merge strategy: {plugins_json_merge_strategy.name}"
                        )
                elif plugins_json_merge_strategy.should_delete:
                    # find the plugins in the reverse_dependencies that are also in the expected_plugins
                    associated_parents = plugins_with_plugin_in_tree(
                        graphs, graph_type_minus_bootstrap, plugin["id"]
                    )
                    expected_parents = ", ".join(
                        associated_parents.intersection(expected_plugins)
                    )
                    logging.trace(  # type: ignore
                        f" -> removing plugin {plugin['id']} (parents: {expected_parents}) according to merge strategy: {plugins_json_merge_strategy.name}"
                    )
                else:
                    logging.warning(
                        f" -> plugin {plugin['id']} found but not removed according to merge strategy: {plugins_json_merge_strategy.name}"
                    )
                    updated_plugins.append(plugin)
            else:
                updated_plugins.append(plugin)

        # check for plugins that are installed and necessary but not in the plugins.yaml file
        # if the plugin is not in the plugins.yaml file, add it
        logging.info(
            f"Looking for plugins that are installed but not in the current plugins.yaml"
        )
        for plugin in expected_plugins:
            found_plugin = find_plugin_by_id(current_plugins, plugin)
            if found_plugin is None:
                if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
                    logging.warning(
                        f" -> found plugin installed on server but not present in bundle (skipping according to merge strategy: {plugins_json_merge_strategy.name}) : {plugin}"
                    )
                else:
                    logging.info(
                        f" -> adding plugin expected but not present (according to strategy: {plugins_json_merge_strategy.name}) : {plugin}"
                    )
                    updated_plugins.append({"id": plugin})

        updated_plugins = sorted(updated_plugins, key=lambda x: x["id"])

        updated_plugins_ids = [plugin["id"] for plugin in updated_plugins]
        all_plugin_ids = set(updated_plugins_ids + expected_plugins)
        show_diff(
            "Final merged plugins < vs > expected plugins after merging",
            all_plugin_ids,
            updated_plugins_ids,
            expected_plugins,
        )
        if plugin_catalog_plugin_ids_previous:
            show_diff(
                "Final merged catalog < vs > previous catalog after merging",
                plugin_catalog_plugin_ids + plugin_catalog_plugin_ids_previous,
                plugin_catalog_plugin_ids,
                plugin_catalog_plugin_ids_previous,
            )

        plugins_data["plugins"] = updated_plugins
        if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
            logging.info(
                f"Skipping writing to plugins.yaml according to merge strategy: {plugins_json_merge_strategy.name}"
            )
        else:
            if original_plugin_data != plugins_data:
                with open(plugins_file, "w", encoding="utf-8") as f:
                    logging.info(f"Writing updated plugins to {plugins_file}")
                    yaml.dump(
                        plugins_data, f
                    )  # Write the updated data back to the file
            else:
                logging.info(f"No changes detected in {plugins_file}. Skipping write.")


def _find_target_dir_upwards(target_dir: str) -> Path | None:
    """Search upwards from target_dir to find a 'target' directory within 4 levels."""
    path = Path(target_dir).resolve()
    for _ in range(5):
        candidate = path / "target"
        if candidate.is_dir():
            return candidate
        path = path.parent
    return None


def remove_files_from_dir(dir, max_depth=1):
    # sanity check - ensure one of the top 4 parents is called target
    if not _find_target_dir_upwards(dir):
        die(
            f"Target directory '{dir}' does not have a 'target' directory in its path. Will not recursively delete."
        )
    # if the dir has more than max_depth sub directories, die
    base = Path(dir).resolve()
    if not base.is_dir():
        die(f"{dir} is not a directory")
    this_depth = 0
    for path in base.rglob("*"):
        if path.is_dir():
            rel_depth = len(path.relative_to(base).parts)
            this_depth = max(this_depth, rel_depth)
    if this_depth > max_depth:
        die(
            f"Directory '{dir}' has {this_depth} levels, which is more than the allowed maximum of {max_depth}. Will not recursively delete."
        )

    # delete files and dirs recursively
    for root, dirs, files in os.walk(dir, topdown=False):
        for name in files:
            file_path = os.path.join(root, name)
            logging.debug(f"Removing file: {file_path}")
            os.remove(file_path)
        for name in dirs:
            dir_path = os.path.join(root, name)
            logging.debug(f"Removing directory: {dir_path}")
            os.rmdir(dir_path)


def _read_core_casc_export_file(url, username, password, filename="bundle.yaml"):
    # read the file from the core-casc-export directory
    url = utilz.join_url(url, f"/core-casc-export/{filename}")
    response_text = call_jenkins_api(url, username, password)
    return response_text


@click.pass_context
def fetch_yaml_docs(ctx, ignore_items, path, url, username, password, target_dir):
    logging.debug(f"Creating target directory: {target_dir}")
    os.makedirs(target_dir, exist_ok=True)

    # remove any existing files
    remove_files_from_dir(target_dir)

    if path:
        # if the path points to a zip file, extract the YAML from the zip file
        if path.endswith(".zip"):
            logging.info(f"Extracting YAML from ZIP file: {path}")
            with zipfile.ZipFile(path, "r") as zip_ref:
                # list the files in the zip file
                for filename in zip_ref.namelist():
                    # read the YAML from the file
                    with zip_ref.open(filename) as f:
                        # if file is empty, skip
                        if f.read(1):
                            f.seek(0)
                            response_text = f.read()
                            response_text = preprocess_yaml_text(response_text)
                            logging.debug(f"Read YAML from file: {filename}")
                            doc = yaml.load(response_text)
                            write_yaml_doc(doc, target_dir, filename)
                        else:
                            logging.warning(f"Skipping empty file: {filename}")
        else:
            logging.info(f"Read YAML from path: {path}")
            with open(path, "r", encoding="utf-8") as f:
                response_text = f.read()
                response_text = preprocess_yaml_text(response_text)
                yaml_docs = list(yaml.load_all(response_text))
                write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    elif url:
        filename = "bundle.yaml"
        response_text = _read_core_casc_export_file(url, username, password, filename)
        response_text = preprocess_yaml_text(response_text)
        doc = yaml.load(response_text)
        write_yaml_doc(doc, target_dir, filename)
        for key in bundle_yaml_keys:
            if key in doc.keys():
                if ignore_items and key == "items":
                    logging.info(
                        f"Not downloading the items.yaml (computationally expensive)"
                    )
                    continue
                # traverse the list under the key
                for filename in doc[key]:
                    export_url = url.rstrip("/") + f"/core-casc-export/{filename}"
                    response_text = call_jenkins_api(export_url, username, password)
                    response_text = preprocess_yaml_text(response_text)
                    doc2 = yaml.load(response_text)
                    write_yaml_doc(doc2, target_dir, filename)
    else:
        die("No path or URL provided")


@click.pass_context
def preprocess_yaml_text(ctx, response_text):
    catalog_warnings_strategy = _get(Key.PLUGINS_CATALOG_WARNINGS_STRATEGY)
    if isinstance(response_text, bytes):
        response_text = response_text.decode("utf-8")
    # if the response is empty, skip
    if not response_text:
        logging.warning("Empty response from server. Skipping.")
        return response_text
    # find any occurrences of "^--- .*$"
    matching_lines = re.findall(r"^--- .*$", response_text, re.MULTILINE)
    if matching_lines:
        # log results
        for line in matching_lines:
            logging.warning(f"Found catalog warnings: {line}")
        if catalog_warnings_strategy == PluginCatalogWarningsStrategy.COMMENT.name:
            logging.warning(
                f"Found catalog warnings in the response. Converting to comments according to strategy {catalog_warnings_strategy}"
            )
            response_text = re.sub(
                r"^--- .*$", r"# \g<0>", response_text, flags=re.MULTILINE
            )
        elif catalog_warnings_strategy == PluginCatalogWarningsStrategy.FAIL.name:
            die(f"""
                    Found catalog warnings in the response. Exiting according to strategy {catalog_warnings_strategy}
                    Either fix the warnings or change the strategy to {PluginCatalogWarningsStrategy.COMMENT.name} to convert warnings to comments.""")
        else:
            die(
                f"Invalid catalog warnings strategy: {catalog_warnings_strategy}. Expected one of: {get_name_from_enum(PluginCatalogWarningsStrategy)}"
            )
    return response_text


def call_jenkins_api(
    url,
    username,
    password,
    data_file: str = "",
    out_file: str = "",
    headers={"Accept": "application/json"},
):
    """
    Call the Jenkins API and return the response text.
    """
    # check the internal_cache for the URL
    if url in internal_cache:
        logging.debug(f"Found URL in internal cache: {url}")
        return internal_cache[url]
    logging.debug(f"Fetching response from URL: {url}")
    logging.trace(f"Using username:` {username}")  # type: ignore
    # print last 5 characters of password
    logging.trace(f"Using password: ...{password[-1:]}")  # type: ignore
    if username and password:
        headers["Authorization"] = "Basic " + base64.b64encode(
            f"{username}:{password}".encode("utf-8")
        ).decode("utf-8")
    if out_file:
        if out_file.endswith(".zip"):
            headers["Accept"] = "application/zip;charset=utf-8"
        elif out_file.endswith(".json"):
            headers["Aceept"] = "application/json"
        elif out_file.endswith(".yaml"):
            headers["Aceept"] = "text/yaml"
        else:
            logging.warning(
                f"Out file {out_file} does not have a recognized extension. Assuming text/plain."
            )
    if data_file:
        # if file is binary, set the headers accordingly
        if data_file.endswith(".zip"):
            headers["Content-Type"] = "application/zip;charset=utf-8"
        elif data_file.endswith(".json"):
            headers["Content-Type"] = "application/json"
        elif data_file.endswith(".yaml"):
            headers["Content-Type"] = "text/yaml"
        else:
            logging.warning(
                f"Data file {data_file} does not have a recognized extension. Assuming text/plain."
            )
        # read the data from the file
        with open(data_file, "rb") as f:
            post_data = f.read()
        response = requests.post(url, data=post_data, headers=headers, verify=False)
        response.raise_for_status()
    else:
        response = requests.get(url, headers=headers)
        response.raise_for_status()

    if out_file:
        # write the response to the out_file
        with open(out_file, "wb") as f:
            f.write(response.content)
        logging.info(f"Wrote response to {out_file}")
    else:
        # add the URL to the internal_cache
        internal_cache[url] = response.text
        return response.text


def write_all_yaml_docs_from_comments(yaml_docs, target_dir):
    # create a new file for each YAML document
    for i, doc in enumerate(yaml_docs):
        # read the header from the original YAML doc
        filename = doc.ca.comment[1][0].value.strip().strip("# ")
        # remove the first line of the comment from the YAML doc
        doc.ca.comment[1].pop(0)
        write_yaml_doc(doc, target_dir, filename)


def write_yaml_doc(doc, target_dir, filename):
    if not doc:
        logging.warning(f"Skipping empty YAML document")
        return
    filename = os.path.join(target_dir, filename)
    doc = preprocess_yaml_object(doc)

    # create a new file for each YAML document
    with open(filename, "w", encoding="utf-8") as f:
        # dump without quotes for strings and without line break at the end
        yaml.dump(doc, f)
        logging.info(f"Wrote {filename}")
    # remove the last empty line break if necessary
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    if lines and lines[-1] == "\n":
        lines = lines[:-1]
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)


def find_paths_of_values_matching_pattern(obj, pattern, path=""):
    """
    Find all paths in the object which have a non-dict/non-list value
    and save as a dict where the path is key and the value is true
    if it matches the pattern, and false otherwise.
    """
    paths = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else f"/{k}"
            if isinstance(v, (dict, list)):
                paths.update(
                    find_paths_of_values_matching_pattern(v, pattern, new_path)
                )
            elif isinstance(v, str) and re.match(pattern, v):
                paths[new_path] = {"value": v, "matches": True}
            else:
                paths[new_path] = {"value": v, "matches": False}
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}/{i}"
            paths.update(find_paths_of_values_matching_pattern(v, pattern, new_path))
    return paths


def hash_me(hash_seed, val):
    """
    Hash the string using SHA256 and return the hex digest.
    """
    # max length of hex should be 24
    return "bu-hash-" + hashlib.sha256((hash_seed + val).encode()).hexdigest()[:24]


def traverse_credentials(
    hash_only,
    hash_seed,
    filename,
    fileobj,
    obj,
    traversed_paths,
    custom_replacements={},
    path="",
):
    """
    Traverse the object and find all paths that match the pattern.
    If a path matches, create a JSON Patch operation to replace the value
    with a replacement string.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else f"/{k}"
            # if the path has already been traversed, skip it
            if new_path in traversed_paths:
                logging.debug(f"1Traversing path (N): {new_path} - already traversed!")
                continue
            if not "id" in obj:
                logging.debug(f"1Traversing path (Y): {new_path}")
                traversed_paths.append(new_path)
            else:
                sub_paths = find_paths_of_values_matching_pattern(
                    obj, r"{AQAAABAAAA[a-zA-Z0-9+/=]{8,}}", ""
                )
                for sub_path, matchesValueDict in sub_paths.items():
                    matches = matchesValueDict["matches"]
                    val = matchesValueDict["value"]
                    # remove the leading slash from the path
                    new_path = f"{path}{sub_path}" if path else f"{sub_path}"
                    if new_path in traversed_paths:
                        logging.debug(
                            f"2Traversing path (N): {new_path} ({matches}) - already traversed!"
                        )
                        continue
                    logging.debug(f"2Traversing path (Y): {new_path} ({matches})")
                    traversed_paths.append(new_path)
                    if sub_path == "/id":
                        logging.debug(f"Skipping path (N): {new_path} - id")
                        continue
                    id = obj["id"]
                    matching_tuple = None
                    # hashing only for auditing purposes - no need to check for custom replacements
                    if not hash_only:
                        custom_replacements_for_id = [
                            item for item in custom_replacements if item["id"] == id
                        ]
                        for custom_replacement in custom_replacements_for_id:
                            # check if the sub_path is in the custom_replacement with or without the leading slash
                            if (
                                sub_path in custom_replacement
                                or sub_path.lstrip("/") in custom_replacement
                            ):
                                logging.debug(
                                    f"Custom replacement found: {custom_replacement} for sub_path {sub_path}"
                                )
                                matching_tuple = custom_replacement
                    if matches or matching_tuple is not None:
                        logging.debug(f"2Traversing2a path (Y): {new_path}")
                        if hash_only:
                            # create a hash of the hash_seed + v
                            replacement = hash_me(hash_seed, val)
                        elif matching_tuple is None:
                            logging.debug(
                                f"Matching tuple NOT found. Creating replacement for {id} and {sub_path}"
                            )
                            # create a string consisting of:
                            # - all non-alphanumeric characters changed to underscores
                            # - the id and k joined with an underscore
                            # - all uppercased
                            logging.debug(
                                f"Creating replacement for {id} and {k} and {sub_path}"
                            )
                            replacement = (
                                "${"
                                + re.sub(
                                    r"\W", "_", id + "_" + sub_path.removeprefix("/")
                                ).upper()
                                + "}"
                            )
                        else:
                            logging.debug(f"Matching tuple found: {matching_tuple}")
                            replacement = matching_tuple[sub_path.removeprefix("/")]

                        if replacement == BUNDLEUTILS_CREDENTIAL_DELETE_SIGN:
                            parent_path = re.sub(r"/[^/]*$", "", path)
                            logging.warning(
                                f"Found a credential '{id}' string that needs to be deleted at path: {parent_path}"
                            )
                            # print the JSON Patch operation for the deletion of the parent object
                            patch = {"op": "remove", "path": f"{parent_path}"}
                            fileobj = apply_patch_obj(filename, fileobj, [patch])
                            break
                        else:
                            # print the JSON Patch operation for the replacement
                            patch = {
                                "op": "replace",
                                "path": f"{new_path}",
                                "value": f"{replacement}",
                            }
                            fileobj = apply_patch_obj(filename, fileobj, [patch])
                continue
            fileobj = traverse_credentials(
                hash_only,
                hash_seed,
                filename,
                fileobj,
                v,
                traversed_paths,
                custom_replacements,
                new_path,
            )
    elif isinstance(obj, list):
        # traverse the list in reverse order to avoid index issues when deleting items
        for i, v in enumerate(reversed(obj)):
            # Calculate the original index by subtracting the reversed index from the length of the list minus 1
            original_index = len(obj) - 1 - i
            new_path = f"{path}/{original_index}"
            fileobj = traverse_credentials(
                hash_only,
                hash_seed,
                filename,
                fileobj,
                v,
                traversed_paths,
                custom_replacements,
                new_path,
            )
    else:
        if isinstance(obj, str) and re.match(r"{.*}", obj):
            # if the string is a replacement string, raise an exception
            logging.warning(
                f"Found a non-credential string (no id found) that needs to be replaced at path: {path}"
            )
            if hash_only:
                # create a hash of the hash_seed + v
                replacement = hash_me(hash_seed, obj)
            else:
                # the replacement string should be in the format ${ID_KEY}
                replacement = (
                    "${" + re.sub(r"\W", "_", path.removeprefix("/")).upper() + "}"
                )
            # print the JSON Patch operation for the replacement
            patch = {"op": "replace", "path": f"{path}", "value": f"{replacement}"}
            fileobj = apply_patch_obj(filename, fileobj, [patch])
    return fileobj


def parse_selector(selector_str):
    return dict(kv.split("=", 1) for kv in selector_str.split(","))


def resolve_paths_with_selectors(data, path):
    """Return a list of all matching resolved paths."""
    parts = path.strip("/").split("/")
    results = []

    def recurse(current, parts_remaining, path_so_far):
        if not parts_remaining:
            results.append(path_so_far)
            return

        part = parts_remaining[0]

        # SELECTOR
        selector_match = selector_pattern.fullmatch(part)
        if selector_match:
            if not isinstance(current, list):
                return
            conditions = parse_selector(selector_match.group(1))
            for i, item in enumerate(current):
                if all(str(item.get(k)) == v for k, v in conditions.items()):
                    recurse(item, parts_remaining[1:], path_so_far + [i])

        # WILDCARD
        elif part == "*":
            if not isinstance(current, list):
                return
            for i, item in enumerate(current):
                recurse(item, parts_remaining[1:], path_so_far + [i])

        # REGULAR
        else:
            key = int(part) if isinstance(current, list) and part.isdigit() else part
            if (
                isinstance(current, list)
                and isinstance(key, int)
                and key < len(current)
            ):
                recurse(current[key], parts_remaining[1:], path_so_far + [key])
            elif isinstance(current, dict) and key in current:
                recurse(current[key], parts_remaining[1:], path_so_far + [key])

    recurse(data, parts, [])
    return results


def expand_patch_paths(obj, patch_list):
    expanded = []

    for patch in patch_list:
        matches = resolve_paths_with_selectors(
            obj, patch["path"]
        )  # use our earlier function
        for path_parts in matches:
            json_ptr = "/" + "/".join(
                str(p).replace("~", "~0").replace("/", "~1") for p in path_parts
            )
            new_patch = patch.copy()
            new_patch["path"] = json_ptr
            expanded.append(new_patch)

    return expanded


def apply_patch_obj(filename, obj, patch_list):
    # Expand wildcard/selector paths before applying
    expanded_patches = expand_patch_paths(obj, patch_list)
    logging.debug(f"Expanded patches:\n{printYaml(expanded_patches)}")

    # for each patch, apply the patch to the object
    for patch in expanded_patches:
        # if not an add operation
        if patch["op"] != "add":
            # Check if the path exists
            try:
                patch_path = patch["path"]
                logging.debug(f"Checking if path exists for patch path: {patch_path}")
                jsonpointer.resolve_pointer(obj, patch_path)
            except jsonpointer.JsonPointerException:
                # If the path does not exist, skip the patch
                logging.debug(
                    f"Ignoring non-existent path {patch['path']} in {filename}."
                )
                continue
        # Apply the patch
        patch = jsonpatch.JsonPatch([patch])
        try:
            logging.debug(f"Applying JSON patch to {filename}")
            logging.debug(f" ->" + str(patch))
            obj = patch.apply(obj)
        except jsonpatch.JsonPatchConflict:
            logging.error("Failed to apply JSON patch")
            return
    return obj


def apply_patch_file(filename, patch_list):
    with open(filename, "r", encoding="utf-8") as inp:
        obj = yaml.load(inp)

    if obj is None:
        logging.error(f"Failed to load YAML object from file {filename}")
        return
    obj = _convert_to_dict(obj)
    # logging.info(f"Transform: start applying patches to {filename}. The file is:\n{printYaml(obj, convert=True)}")
    obj = apply_patch_obj(filename, obj, patch_list)
    # logging.info(f"Transform: stopped applying patches to {filename}. The file is now:\n{printYaml(obj, convert=True)}")

    # save the patched object back to the file
    with open(filename, "w", encoding="utf-8") as out:
        yaml.dump(obj, out)


def handle_patches(patches, target_dir):
    # if patches is empty, skip
    if not patches:
        logging.info("Transform: no JSON patches to apply")
        return
    # for each key in the patches, open the file and apply the patch
    for filename, patch in patches.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            logging.info(f"File {filename} does not exist. Skipping patching.")
            continue
        logging.info(f"Transform: applying JSON patches to {filename}")
        apply_patch_file(filename, patch)


@click.pass_context
def apply_replacements(ctx, filename, custom_replacements):
    with open(filename, "r", encoding="utf-8") as inp:
        obj = yaml.load(inp)
        if obj is None:
            logging.error(f"Failed to load YAML object from file {filename}")
            return
        hash_only = utilz.is_truthy(_get(Key.AUDIT_HASH, "false"))
        hash_seed = ctx.obj.get("hash_seed", "")
        if hash_only:
            if hash_seed is None or hash_seed == "":
                logging.info(f"Hashing encrypted data without seed")
            else:
                logging.info(f"Hashing encrypted data with seed")
        fileobj = _convert_to_dict(obj)
        # logging.info(f"Transform: start applying replacements to {filename}")
        fileobj = traverse_credentials(
            hash_only, hash_seed, filename, fileobj, obj, [], custom_replacements
        )
        # logging.info(f"Transform: stopped applying replacements to {filename}. The file is now:\n{printYaml(fileobj, convert=True)}")
        # save the patched object back to the file
        with open(filename, "w", encoding="utf-8") as out:
            yaml.dump(fileobj, out)
            logging.info(f"Wrote {filename}")


def handle_credentials(credentials, target_dir):
    # if credentials is empty, skip
    if not credentials:
        logging.info("Transform: no credentials to replace")
        return
    # for each key in the patches, open the file and apply the patch
    for filename, replacements in credentials.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            continue
        logging.info(f"Transform: applying cred replacements to {filename}")
        apply_replacements(filename, replacements)


def handle_substitutions(substitutions, target_dir):
    # if substitutions is empty, skip
    if not substitutions:
        logging.info("Transform: no substitutions to apply")
        return
    # for each key in the patches, open the file and apply the patch
    for filename, replacements in substitutions.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            continue
        logging.info(f"Transform: applying substitutions to {filename}")
        with open(filename, "r", encoding="utf-8") as inp:
            # use pattern as a regex to replace the text in the file
            text = inp.read()
            for replacement in replacements:
                pattern = replacement["pattern"]
                value = replacement["value"]
                logging.debug(f"Applying substitution: {pattern} -> {value}")
                text = re.sub(pattern, value, text)
            with open(filename, "w", encoding="utf-8") as out:
                out.write(text)
            logging.info(f"Wrote {filename}")


def handle_splits(splits, target_dir):
    # if splits is empty, skip
    if not splits:
        logging.info("Transform: no splits to apply")
        return
    # for type in items, jcasc, if the key exists, process
    for split_type, split_dict in splits.items():
        if split_type == "items":
            for filename, configs in split_dict.items():
                logging.info(
                    f"Transform: applying item split to {target_dir}/{filename}"
                )
                logging.debug(f"Using configs: {configs}")
                split_items(target_dir, filename, configs)
        elif split_type == "jcasc":
            for filename, configs in split_dict.items():
                logging.info(f"Applying jcasc split to {target_dir}/{filename}")
                logging.debug(f"Using configs: {configs}")
                split_jcasc(target_dir, filename, configs)


def _convert_to_dict(obj):
    """Recursively convert CommentedMap and CommentedSeq to dict and list."""
    if isinstance(obj, dict):
        return {k: _convert_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dict(v) for v in obj]
    return obj


def printYaml(obj, convert=False, custom_yaml=None):
    # needed to remove comments and '!!omap' identifiers
    obj2 = _convert_to_dict(obj) if convert else obj
    stream = io.StringIO()
    if custom_yaml:
        # Use custom YAML dumper if provided
        custom_yaml.dump(obj2, stream)
    else:
        yaml.dump(obj2, stream)
    return stream.getvalue()


def uncomment(obj2):
    if isinstance(obj2, CommentedMap):
        # Remove item comments
        for key in list(obj2.ca.items.keys()):
            obj2.ca.items[key] = [None, None, None, None]
        # Remove own comments
        obj2.ca.comment = None
    elif isinstance(obj2, CommentedSeq):
        # Remove item comments
        for idx in range(len(obj2)):
            obj2.ca.items[idx] = [None, None, None, None]
        # Remove own comments
        obj2.ca.comment = [None, None, None, None]
    return obj2


def recursive_merge(obj1, obj2):
    logging.trace(f"Obj1 ----> Key: {type(obj1)} Value: {obj1}")  # type: ignore
    logging.trace(f"Obj2 ----> Key: {type(obj2)} Value: {obj2}")  # type: ignore

    if isinstance(obj2, (CommentedMap, dict)):
        for key, value in obj2.items():
            if key not in obj1 or obj1[key] is None:
                logging.trace(f"Adding new key: {key} with value: {value}")  # type: ignore
                if isinstance(value, (CommentedMap, dict)):
                    obj1[key] = recursive_merge({}, uncomment(value))
                elif isinstance(value, (CommentedSeq, list)):
                    obj1[key] = recursive_merge([], uncomment(value))
                else:
                    obj1[key] = uncomment(value)
            else:
                logging.trace(f"Merging key: {key} with value: {value}")  # type: ignore
                obj1[key] = recursive_merge(obj1[key], uncomment(value))
    elif isinstance(obj2, (CommentedSeq, list)):
        for value in obj2:
            if value not in obj1:
                obj1.append(uncomment(value))
    else:
        logging.trace(f"Unkown type: {type(obj2)}")  # type: ignore
    return obj1


@click.pass_context
def _file_check(ctx, file, strict=False):
    # if file does not exist, or is empty, skip
    logging.debug(f"Checking file: {file}")
    # resolve the file to a relative path
    file = os.path.abspath(file)
    if not os.path.exists(file) or os.path.getsize(file) == 0:
        # if default_fail_on_missing is set, raise an exception
        if ctx.params["strict"] or strict:
            die(f"File {file} does not exist")
        logging.warning(f"File {file} does not exist. Skipping.")
        return False
    return True


@bundleutils.command()
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.URL)
@option_for(Key.DRY_RUN, default="False", type=click.BOOL)
@option_for(Key.STRICT, default="False", type=click.BOOL)
@option_for(
    Key.CONFIGS_BASE,
    type=click.Path(file_okay=False, dir_okay=True),
    default=default_config_base,
)
@option_for(Key.CONFIG, type=click.Path(file_okay=True, dir_okay=False))
@option_for(Key.AUDIT_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.AUDIT_TARGET_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.AUDIT_HASH_SEED, default="")
@option_for(Key.AUDIT_HASH, default="True", type=click.BOOL)
@click.pass_context
def audit(
    ctx,
    config_key,
    url,
    dry_run,
    strict,
    configs_base,
    config,
    source_dir,
    target_dir,
    hash_seed,
    hash,
):
    """
    Transform bundle but obfuscating any sensitive data.

    \b
    NOTE:
    - The credentials and sensitive data will be hashed and cannot be used in an actual bundle.
    - Use the hash arg to revert to the standard method.

    """

    if not config_key in ["ALL", "NONE"]:
        logging.getLogger().setLevel(logging.WARNING)
    dry_run = utilz.is_truthy(_get(Key.DRY_RUN, dry_run))
    strict = utilz.is_truthy(_get(Key.STRICT, strict))
    configs_base = _get(Key.CONFIGS_BASE, configs_base)
    hash_seed = _get(Key.AUDIT_HASH_SEED, hash_seed, required=False)
    hash = utilz.is_truthy(_get(Key.AUDIT_HASH, hash))

    url = str(_get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False))
    config = _determine_transformation_config(url, config)
    merged_config = _get_merged_config(config)
    if dry_run:
        logging.info(f"Merged config:\n" + printYaml(merged_config))
        return

    source_dir = _get(Key.AUDIT_SOURCE_DIR, source_dir, required=False)
    target_dir = _get(Key.AUDIT_TARGET_DIR, target_dir, required=False)
    if not source_dir or not target_dir:
        passed_dirs = {}
        passed_dirs[Key.AUDIT_SOURCE_DIR] = source_dir
        passed_dirs[Key.AUDIT_TARGET_DIR] = target_dir
        _add_default_dirs_if_necessary(url, None, passed_dirs)
    source_dir = os.path.normpath(str(_get(Key.AUDIT_SOURCE_DIR)))
    target_dir = os.path.normpath(str(_get(Key.AUDIT_TARGET_DIR)))

    if _print_config(config_key):
        return

    # set the is_audit flag for the bundle update later (we want to set the version later)
    os.environ[BUNDLEUTILS_AUDIT_FIXED_VERSION] = "AUDITED_BUNDLE_DO_NOT_USE"

    _transform(merged_config, source_dir, target_dir, dry_run)


@bundleutils.command()
@option_for(Key.CONFIG_KEY, is_flag=False, flag_value="ALL", default="NONE")
@option_for(Key.URL)
@option_for(Key.DRY_RUN, default="False", type=click.BOOL)
@option_for(Key.STRICT, default="False", type=click.BOOL)
@option_for(
    Key.CONFIGS_BASE,
    type=click.Path(file_okay=False, dir_okay=True),
    default=default_config_base,
)
@option_for(Key.CONFIG, type=click.Path(file_okay=True, dir_okay=False))
@option_for(Key.TRANSFORM_SOURCE_DIR, type=click.Path(file_okay=False, dir_okay=True))
@option_for(Key.TRANSFORM_TARGET_DIR, type=click.Path(file_okay=False, dir_okay=True))
@click.pass_context
def transform(
    ctx, config_key, url, dry_run, strict, configs_base, config, source_dir, target_dir
):
    """Transform using a custom transformation config."""
    if not config_key in ["ALL", "NONE"]:
        logging.getLogger().setLevel(logging.WARNING)
    dry_run = utilz.is_truthy(_get(Key.DRY_RUN, dry_run))
    strict = utilz.is_truthy(_get(Key.STRICT, strict))
    configs_base = _get(Key.CONFIGS_BASE, configs_base)

    url = str(_get(Key.URL, url, default=f"{_get(Key.DEDUCED_URL)}", required=False))
    config = _determine_transformation_config(url, config)
    merged_config = _get_merged_config(config)
    if dry_run:
        logging.info("Dry run mode enabled. No transformations will be applied.")
        logging.info(f"Merged config:\n" + printYaml(merged_config))
        return

    source_dir = _get(Key.TRANSFORM_SOURCE_DIR, source_dir, required=False)
    target_dir = _get(Key.TRANSFORM_TARGET_DIR, target_dir, required=False)
    if not source_dir or not target_dir:
        passed_dirs = {}
        passed_dirs[Key.TRANSFORM_SOURCE_DIR] = source_dir
        passed_dirs[Key.TRANSFORM_TARGET_DIR] = target_dir
        _add_default_dirs_if_necessary(url, None, passed_dirs)
    source_dir = os.path.normpath(str(_get(Key.TRANSFORM_SOURCE_DIR)))
    target_dir = os.path.normpath(str(_get(Key.TRANSFORM_TARGET_DIR)))

    if _print_config(config_key):
        return
    _transform(merged_config, source_dir, target_dir, dry_run)


def _get_merged_config(config):
    """
    Get the merged configuration from the config file.
    It is assumed to be a path to a YAML file.
    If the loaded config has an 'includes' section,
    it will recursively include other YAML files specified in that section.
    """
    if not config:
        die("No transformation config provided and no default config found.")
    if not os.path.exists(config):
        die(f"Transformation config file {config} does not exist.")
    if not os.path.isfile(config):
        die(f"Transformation config {config} is not a file.")
    logging.debug(f"Transformation: processing {config}")
    with open(config, "r", encoding="utf-8") as inp:
        merged_config = yaml.load(inp)
    if not merged_config:
        die(f"Transformation config {config} is empty or invalid YAML.")
    # if the config has an 'includes' section, recursively include other YAML files
    # the entries are assumed to be relative to the config file's directory
    if "includes" in merged_config:
        includes = merged_config["includes"]
        if isinstance(includes, str):
            includes = [includes]
        for include in includes:
            include_path = os.path.join(os.path.dirname(config), include)
            if not os.path.exists(include_path):
                die(f"Included config file {include_path} does not exist.")
            included_config = _get_merged_config(include_path)
            merged_config = recursive_merge(included_config, merged_config)
    # remove the 'includes' section from the merged config
    merged_config.pop("includes", None)
    return merged_config


def _transform(merged_config, source_dir, target_dir, dry_run=False):
    """Transform using a custom transformation config."""
    logging.debug(f"Merged config:\n" + printYaml(merged_config))
    source_dir = os.path.normpath(source_dir)
    if not target_dir:
        die(f"Target directory is not set. Please provide a target directory.")
    target_dir = os.path.normpath(target_dir)
    logging.info(f"Transform: source {source_dir} to target {target_dir}")
    # create the target directory if it does not exist, delete all files in it
    os.makedirs(target_dir, exist_ok=True)
    for filename in os.listdir(target_dir):
        filename = os.path.join(target_dir, filename)
        os.remove(filename)
    # copy all files from the source directory to the target directory
    for filename in os.listdir(source_dir):
        source_filename = os.path.join(source_dir, filename)
        target_filename = os.path.join(target_dir, filename)
        logging.debug(f"Copying {source_filename} to {target_filename}")
        with open(source_filename, "r", encoding="utf-8") as inp:
            obj = yaml.load(inp)
        with open(target_filename, "w", encoding="utf-8") as out:
            yaml.dump(obj, out)

    handle_patches(merged_config.get("patches", {}), target_dir)
    handle_credentials(merged_config.get("credentials", []), target_dir)
    handle_substitutions(merged_config.get("substitutions", {}), target_dir)
    handle_splits(merged_config.get("splits", {}), target_dir)
    _update_bundle(target_dir)


@click.pass_context
def preprocess_yaml_object(ctx, data, parent_key=None):
    if isinstance(data, CommentedMap):
        # Remove empty keys
        keys_to_remove = [k for k in data if k == ""]
        if keys_to_remove:
            logging.debug(f"Removed empty keys from {type(data)}: {data}")
            for key in keys_to_remove:
                del data[key]
        # Convert values to block scalars if needed
        convert_to_scalars = [
            k
            for k in data
            if k in _get(Key.FETCH_KEYS_TO_SCALARS) and data[k] is not None
        ]
        for key in convert_to_scalars:
            if key in data and isinstance(data[key], str) and data[key].strip():
                data[key] = scalarstring.LiteralScalarString(data[key])
        for key, value in data.items():
            preprocess_yaml_object(value, key)  # Recursively process nested items
    elif isinstance(data, (CommentedSeq, list)):
        items_to_keep = []
        items_to_ignore = []
        for item in data:
            # Special case: `env` list with dicts that have only 'key'
            if parent_key == "env" and isinstance(item, dict):
                if list(item.keys()) == ["key"]:  # only 'key' present
                    logging.warning(
                        f"MISSING VALUE STRING - BEE-29822: Adding value = '' to entry for key: {item['key']}"
                    )
                    item["value"] = ""
            processed_item = preprocess_yaml_object(item, parent_key)
            if processed_item or processed_item == 0:
                items_to_keep.append(processed_item)
            else:
                items_to_ignore.append(item)
        if items_to_ignore:
            logging.debug(f"Removed empty items from {parent_key}: {items_to_ignore}")
        data[:] = items_to_keep
    # For scalar values, just return as-is
    return data


def _find_bundles(target_dir):
    # find all bundle.yaml files in the target directory
    bundles = []
    for root, dirs, files in os.walk(target_dir):
        # ignore any target directories
        if "target" in dirs:
            dirs.remove("target")
        # check if the bundle.yaml file exists in the directory
        for file in files:
            if file == "bundle.yaml":
                # if the bundle.yaml file is in the target directory, skip it
                if os.path.abspath(root) == os.path.abspath(target_dir):
                    continue
                bundles.append(root)
    return bundles


@bundleutils.command()
@click.option(
    "-t",
    "--target-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    help=f"The target directory to find bundles (defaults to CWD).",
)
@click.pass_context
def find_bundles(ctx, target_dir):
    """
    Find all bundle.yaml files in the target directory and print their paths.
    If no target directory is provided, the current working directory is used.
    """
    if not target_dir:
        target_dir = os.curdir
    for bundle_path in _find_bundles(target_dir):
        click.echo(bundle_path)


@bundleutils.command()
@option_for(
    Key.UPDATE_BUNDLE_TARGET_DIR,
    type=click.Path(file_okay=False, dir_okay=True),
    default=os.getcwd(),
)
@option_for(Key.UPDATE_BUNDLE_DESCRIPTION)
@option_for(Key.UPDATE_BUNDLE_OUTPUT_SORTED)
@option_for(Key.UPDATE_BUNDLE_EMPTY_BUNDLE_STRATEGY)
@option_for(Key.UPDATE_BUNDLE_RECURSIVE, default="False", type=click.BOOL)
@click.pass_context
def update_bundle(
    ctx, target_dir, description, output_sorted, empty_bundle_strategy, recursive
):
    """
    \b
    Update the bundle.yaml file in the target directory:
    - Updating keys according to the files found
    - Removing keys that have no files
    - Generating a new UUID for the id key

    \b
    Bundle version generation:
    - Sorts files alphabetically to ensure consistent order.
    - Sorts YAML keys recursively inside each file.
    - Generates a SHA-256 hash and converts it into a UUID.

    \b
    Empty bundle strategy must be one of:
    - 'fail': Fail if the bundle is empty.
    - 'delete': Delete the bundle if it is empty
    - 'noop': Create a noop jenkins.yaml and continue

    """
    if recursive:
        target_dir = os.path.normpath(target_dir)
        bundle_paths = _find_bundles(target_dir)
        if not bundle_paths:
            die(f"No bundle.yaml files found in {target_dir}")
        for bundle_path in bundle_paths:
            relative_path = os.path.relpath(bundle_path, target_dir)
            rel_output_sorted = (
                os.path.join(output_sorted, relative_path) if output_sorted else None
            )
            _update_bundle(
                bundle_path,
                description,
                rel_output_sorted,
                empty_bundle_strategy,
            )
    else:
        _update_bundle(target_dir, description, output_sorted, empty_bundle_strategy)


def _basename(dir):
    return os.path.basename(os.path.normpath(dir))


def _get_files_for_key(target_dir, key):
    files = []
    # Special case for 'jcasc'
    if key == "jcasc":
        prefixes = ["jenkins", "jcasc"]
    elif key == "catalog":
        prefixes = ["plugin-catalog"]
    else:
        prefixes = [key]

    for prefix in prefixes:
        # Add list of YAML files matching .*prefix.* and ending with .yaml
        for file in os.listdir(target_dir):
            if re.match(rf".*{prefix}.*\.yaml", file) and not file == f"{prefix}.yaml":
                files.append(os.path.join(target_dir, file))
    files = sorted(files)

    for prefix in prefixes:
        # if exact match exists, add to front
        exact_match = os.path.join(target_dir, f"{prefix}.yaml")
        if os.path.exists(exact_match):
            logging.debug(f"Found exact match for {key}: {exact_match}")
            files.insert(0, exact_match)
            break

    # remove any empty files
    files = [file for file in files if _file_check(file)]
    for file in files:
        logging.debug(f"File for {key}: {file}")

    # special case for 'plugins'. If any of the files does not contain the yaml key 'plugins', remove the key from the data
    if key == "jcasc":
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                jcasc_file = yaml.load(f)
                # if jenkins the only key and jenkins is empty, remove the file from the list
                if jcasc_file.keys() == ["jenkins"] and not jcasc_file["jenkins"]:
                    logging.info(
                        f"Removing {file} from the list due to missing or empty jenkins"
                    )
                    files.remove(file)

    # special case for 'plugins'. If any of the files does not contain the yaml key 'plugins', remove the key from the data
    if key == "plugins":
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                plugins_file = yaml.load(f)
                # if no plugins key or plugins is empty, remove the file from the list
                if "plugins" not in plugins_file or not plugins_file["plugins"]:
                    logging.info(
                        f"Removing {file} from the list due to missing or empty plugins"
                    )
                    files.remove(file)
                    os.remove(file)

    # special case for 'catalog'. If any of the files does not contain the yaml key 'configurations', remove the key from the data
    if key == "catalog":
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                catalog_file = yaml.load(f)
                # if no configurations key or configurations is empty, remove the file from the list
                if (
                    "configurations" not in catalog_file
                    or not catalog_file["configurations"]
                ):
                    logging.info(
                        f"Removing {file} from the list due to missing or empty configurations"
                    )
                    files.remove(file)
                    os.remove(file)

    # special case for 'items'. If any of the files does not contain the yaml key 'items', remove the key from the data
    if key == "items":
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                items_file = yaml.load(f)
                # if no items key or items is empty, remove the file from the list
                if "items" not in items_file or not items_file["items"]:
                    logging.info(
                        f"Removing {file} from the list due to missing or empty items"
                    )
                    files.remove(file)
                    os.remove(file)

    # special case for 'rbac'. If any of the files does not contain the yaml key 'roles' and 'groups', remove the key from the data
    if key == "rbac":
        for file in files:
            with open(file, "r", encoding="utf-8") as f:
                rbac_file = yaml.load(f)
                # if no roles key or roles is empty, remove the file from the list
                if ("roles" not in rbac_file or not rbac_file["roles"]) and (
                    "groups" not in rbac_file or not rbac_file["groups"]
                ):
                    logging.info(
                        f"Removing {file} from the list due to missing or empty roles and groups"
                    )
                    files.remove(file)
                    os.remove(file)
    logging.debug(f"Files for {key}: {files}")
    return files


@click.pass_context
def _update_bundle(
    ctx, target_dir, description=None, output_sorted=None, empty_bundle_strategy=None
):
    description = _get(Key.UPDATE_BUNDLE_DESCRIPTION, description, required=False)
    empty_bundle_strategy = _get(
        Key.UPDATE_BUNDLE_EMPTY_BUNDLE_STRATEGY,
        empty_bundle_strategy,
        default_empty_bundle_strategy,
    )
    if not target_dir:
        die("Target directory is not set. Please provide a target directory.")
    logging.debug(f"Updating bundle in {target_dir}")
    # Load the YAML file
    with open(os.path.join(target_dir, "bundle.yaml"), "r", encoding="utf-8") as file:
        data = yaml.load(file)

    all_files = []
    # Iterate over the bundle_yaml_keys
    for key in bundle_yaml_keys.keys():
        files = _get_files_for_key(target_dir, key)

        # Remove the target_dir path and sort the files, ensuring exact match come first
        files = [_basename(file) for file in files]

        # if no files found, remove the key from the data if it exists
        if not files:
            if key in data:
                logging.info(
                    f"Removing key {key} from the bundle as no files were found"
                )
                del data[key]
            continue

        # Update the key in the data
        logging.debug(f"Updated {key} to {files}")
        data[key] = files

        # Add the files to the all_files list
        all_files.extend(files)

    if len(all_files) == 0:
        if empty_bundle_strategy == "delete":
            logging.warning(
                f"Empty Bundle Strategy: No files found. Removing target directory {target_dir}"
            )
            shutil.rmtree(target_dir)
            return
        elif empty_bundle_strategy == "fail":
            die(
                f"Empty Bundle Strategy: No files found for bundle.yaml {target_dir}/bundle.yaml"
            )
        elif empty_bundle_strategy == "noop":
            logging.info(
                "Empty Bundle Strategy: No files found. Creating an empty jenkins.yaml"
            )
            data["jcasc"] = "jenkins.yaml"
            with open(
                os.path.join(target_dir, "jenkins.yaml"), "w", encoding="utf-8"
            ) as file:
                yaml.dump({"jenkins": {}}, file)
        else:
            die(
                f"Empty Bundle Strategy: Strategy '{empty_bundle_strategy}' not supported. {Key.UPDATE_BUNDLE_EMPTY_BUNDLE_STRATEGY.envvar[0]} must be one of {empty_bundle_strategies}"
            )

    # update the id key with the basename of the target_dir
    data["id"] = _basename(target_dir)
    data["description"] = f"Bundle for {data['id']}" if not description else description

    if BUNDLEUTILS_AUDIT_FIXED_VERSION in os.environ:
        # if the bundle is an audit, set the version to the fixed version
        data["version"] = os.environ[BUNDLEUTILS_AUDIT_FIXED_VERSION]
    else:
        data["version"] = generate_collection_uuid(target_dir, all_files, output_sorted)

    # turn apiVersion into an int
    if "apiVersion" in data:
        data["apiVersion"] = int(data["apiVersion"])
    # ensure any keys present in the data are in the order of the bundle_yaml_keys
    for key in bundle_yaml_keys.keys():
        if key in data:
            # remove the key from the data
            value = data.pop(key)
            # add it back in the correct order
            data[key] = value

    # Save the YAML file
    logging.info(f"Updated version to {data['version']} in {target_dir}/bundle.yaml")
    with open(os.path.join(target_dir, "bundle.yaml"), "w", encoding="utf-8") as file:
        yaml.dump(data, file)


def _get_relative_path(target_path, source_path):
    """Get the relative path from source_path to target_path."""
    try:
        return os.path.relpath(target_path, source_path)
    except ValueError as e:
        return target_path


def get_nested(data, path):
    """Get a nested item from a dictionary."""
    keys = path.split("/")
    for key in keys:
        if key in data:
            data = data[key]
        else:
            return None
    return data


def set_nested(data, path, value):
    """Set a nested item in a dictionary."""
    keys = path.split("/")
    finaldest = data
    for key in keys[:-1]:
        data.setdefault(key, {})
        finaldest = data[key]
    finaldest[keys[-1]] = value


def del_nested(data, path):
    """Delete a nested item from a dictionary."""
    keys = path.split("/")
    for key in keys[:-1]:
        data = data[key]
    del data[keys[-1]]


def split_jcasc(target_dir, filename, configs):
    logging.info("Loading YAML object")

    full_filename = os.path.join(target_dir, filename)
    if not _file_check(full_filename):
        return
    with open(full_filename, "r", encoding="utf-8") as f:
        source_data = yaml.load(f)

    # For each target in the configuration...
    for config in configs:
        target = config["target"]
        paths = config["paths"]

        # NOTE on paths:
        # - the path may have an asterisk at the end and after the last slash
        # - this will to affect all keys under that path
        # - this can only happen in conjunction with the 'auto' or 'delete' target
        # - if either of these conditions are not met, it will error out
        new_paths = []
        for path in paths:
            if path.endswith("/*"):
                if target != "auto" and target != "delete":
                    die(f'Path {path} must use target "auto" or "delete"')
                logging.debug(f"Moving all keys under {path} to {target}")
                if path == "/*":
                    path = ""
                    data = source_data
                else:
                    path = path[:-2]
                    data = get_nested(source_data, path)
                if data is None:
                    logging.info(f"No data found at {path}")
                    continue
                for key in data.keys():
                    if path:
                        logging.debug(f" - > {path}/{key}")
                        new_paths.append(f"{path}/{key}")
                    else:
                        logging.debug(f" - > {key}")
                        new_paths.append(f"{key}")
            else:
                # delete leading slash if it exists
                if path.startswith("/"):
                    logging.debug(f"Removing leading slash from path: {path}")
                    path = path[1:]
                new_paths.append(path)

        logging.debug(f"Old paths before wildcards: {new_paths}")
        logging.debug(f"New paths after wildcards: {new_paths}")
        logging.trace(f"Source data: \n{printYaml(source_data)}")  # type: ignore

        # For each path to move...
        for path in new_paths:
            # Check if the path exists in the source file
            if get_nested(source_data, path) is not None:
                # Determine the target file name
                if target == "auto":
                    target_file = path.replace("/", ".") + ".yaml"
                else:
                    target_file = target

                if target_file == "delete":
                    logging.info(f"Deleting {path}")
                    del_nested(source_data, path)
                else:
                    target_file = os.path.join(target_dir, "jenkins." + target_file)
                    logging.debug(f"Moving {path} to {target_file}")

                    # Load the target file if it exists, or create a new one if it doesn't
                    if os.path.exists(target_file):
                        logging.debug(f"Loading existing target file {target_file}")
                        with open(target_file, "r", encoding="utf-8") as file:
                            target_data = yaml.load(file)
                    else:
                        logging.debug(f"Creating new target file {target_file}")
                        target_data = {}

                    # Move the path from the source file to the target file
                    set_nested(target_data, path, get_nested(source_data, path))
                    del_nested(source_data, path)

                    # Save the target file
                    if target_data:
                        logging.info(f"Saving target file {target_file}")
                        with open(target_file, "w", encoding="utf-8") as file:
                            yaml.dump(target_data, file)
                    else:
                        logging.info(
                            f"No data found at {path}. Skipping saving target file {target_file}"
                        )
            else:
                logging.debug(f"Path {path} not found in source file")

    # Save the modified source file if it has any data left
    if source_data:
        logging.info(f"Saving source file {full_filename}")
        with open(full_filename, "w", encoding="utf-8") as file:
            yaml.dump(source_data, file)
        # rename the source files base name to "'jenkins.' + filename" if not already done
        if not filename.startswith("jenkins."):
            new_filename = os.path.join(target_dir, "jenkins." + filename)
            logging.info(f"Renaming {full_filename} to {new_filename}")
            os.rename(full_filename, new_filename)
    else:
        logging.info(f"No data left in source file. Removing {full_filename}")
        os.remove(full_filename)


def split_items(target_dir, filename, configs):
    logging.debug(f"Loading YAML object from {filename}")

    full_filename = os.path.join(target_dir, filename)
    if not _file_check(full_filename):
        return
    with open(full_filename, "r", encoding="utf-8") as f:
        data = yaml.load(f)

    new_data = {}
    removed_items = []

    # if items exist in the source file...
    if "items" not in data:
        logging.info(f"No items found in {full_filename}")
        items = []
    else:
        items = data["items"]
    for config in configs:
        target = config["target"]
        for item in items:
            if item in removed_items:
                continue
            item_name = item["name"]
            logging.info(f"Checking item {item_name} (target: {target})")
            for pattern in config["patterns"]:
                logging.info(f"Checking for pattern {pattern}")
                if re.match(pattern, item_name):
                    logging.info(f" - > matched {item_name}")
                    if target == "auto":
                        target_file = item_name + ".yaml"
                    else:
                        target_file = target
                    removed_items.append(item)
                    if target_file == "delete":
                        logging.info(f" - > ignoring {item_name} to {target_file}")
                    else:
                        if target_file not in new_data:
                            new_data[target_file] = []
                        new_data[target_file].append(item)
                        logging.info(f" - > moving {item_name} to {target_file}")

    # Remove the items that were moved
    for item in removed_items:
        items.remove(item)
    # if there are no items left, remove the file instead of dumping it
    if not items:
        logging.info(f"No items left in file. Removing {full_filename}")
        os.remove(full_filename)
    else:
        # Save the modified source file
        with open(full_filename, "w", encoding="utf-8") as f:
            yaml.dump(data, f)

    # rename the source files base name to "'items.' + filename" if not already done
    if not filename.startswith("items."):
        new_filename = os.path.join(target_dir, "items." + filename)
        logging.info(f"Renaming {full_filename} to {new_filename}")
        os.rename(full_filename, new_filename)

    logging.info(f"Writing files to {target_dir}")
    for pattern_filename, items in new_data.items():
        new_file_path = os.path.join(target_dir, "items." + pattern_filename)
        logging.info(f"Writing {new_file_path}")
        with open(new_file_path, "w", encoding="utf-8") as f:
            yaml.dump({"removeStrategy": data["removeStrategy"], "items": items}, f)


if getattr(sys, "frozen", False):
    bundleutils(sys.argv[1:])
