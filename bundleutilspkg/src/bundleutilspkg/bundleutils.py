from enum import Enum, auto
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid
from bundleutilspkg.utils import get_config_file
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

yaml = YAML(typ='rt')

script_name = os.path.basename(__file__).replace('.py', '')
script_name_upper = script_name.upper()

plugin_json_url_path = '/manage/pluginManager/api/json?pretty&depth=1&tree=plugins[*[*]]'
fetch_url_path = '/core-casc-export'
validate_url_path = '/casc-bundle-mgnt/casc-bundle-validate'
empty_bundle_strategies = ['fail', 'delete', 'noop']
default_target = 'target/docs'
default_auto_env_file = 'bundle-profiles.yaml'
default_bundle_api_version = '2'
default_keys_to_scalars = ['systemMessage','script','description']
default_empty_bundle_strategy = 'delete'

bundle_yaml_keys = {'jcasc': 'jenkins.yaml', 'items': 'items.yaml', 'plugins': 'plugins.yaml', 'rbac': 'rbac.yaml', 'catalog': 'plugin-catalog.yaml', 'variables': 'variables.yaml'}
selector_pattern = re.compile(r"\{\{select\s+\"([^\"]+)\"\s*\}\}")

# environment variables
BUNDLEUTILS_CI_VERSION = 'BUNDLEUTILS_CI_VERSION'
BUNDLEUTILS_CI_TYPE = 'BUNDLEUTILS_CI_TYPE'
BUNDLEUTILS_CI_SERVER_HOME = 'BUNDLEUTILS_CI_SERVER_HOME'
BUNDLEUTILS_CI_MAX_START_TIME = 'BUNDLEUTILS_CI_MAX_START_TIME'
BUNDLEUTILS_LOG_LEVEL = 'BUNDLEUTILS_LOG_LEVEL'
BUNDLEUTILS_AUTO_ENV_FILE = 'BUNDLEUTILS_AUTO_ENV_FILE'
BUNDLEUTILS_ENV = 'BUNDLEUTILS_ENV'
BUNDLEUTILS_ENV_OVERRIDE = 'BUNDLEUTILS_ENV_OVERRIDE'
BUNDLEUTILS_USE_PROFILE = 'BUNDLEUTILS_USE_PROFILE'
BUNDLEUTILS_EMPTY_BUNDLE_STRATEGY = 'BUNDLEUTILS_EMPTY_BUNDLE_STRATEGY'
BUNDLEUTILS_KEYS_TO_CONVERT_TO_SCALARS = 'BUNDLEUTILS_KEYS_TO_CONVERT_TO_SCALARS'
BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR = 'BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR'
BUNDLEUTILS_BOOTSTRAP_SOURCE_BASE = 'BUNDLEUTILS_BOOTSTRAP_SOURCE_BASE'
BUNDLEUTILS_BOOTSTRAP_PROFILE = 'BUNDLEUTILS_BOOTSTRAP_PROFILE'
BUNDLEUTILS_BOOTSTRAP_UPDATE = 'BUNDLEUTILS_BOOTSTRAP_UPDATE'
BUNDLEUTILS_SETUP_SOURCE_DIR = 'BUNDLEUTILS_SETUP_SOURCE_DIR'
BUNDLEUTILS_VALIDATE_EXTERNAL_RBAC = 'BUNDLEUTILS_VALIDATE_EXTERNAL_RBAC'
BUNDLEUTILS_VALIDATE_SOURCE_DIR = 'BUNDLEUTILS_VALIDATE_SOURCE_DIR'
BUNDLEUTILS_TRANSFORM_SOURCE_DIR = 'BUNDLEUTILS_TRANSFORM_SOURCE_DIR'
BUNDLEUTILS_TRANSFORM_TARGET_DIR = 'BUNDLEUTILS_TRANSFORM_TARGET_DIR'
BUNDLEUTILS_TRANSFORM_CONFIGS = 'BUNDLEUTILS_TRANSFORM_CONFIGS'
BUNDLEUTILS_AUDIT_SOURCE_DIR = 'BUNDLEUTILS_AUDIT_SOURCE_DIR'
BUNDLEUTILS_AUDIT_TARGET_DIR = 'BUNDLEUTILS_AUDIT_TARGET_DIR'
BUNDLEUTILS_AUDIT_TARGET_BASE_DIR = 'BUNDLEUTILS_AUDIT_TARGET_BASE_DIR'
BUNDLEUTILS_AUDIT_CONFIGS = 'BUNDLEUTILS_AUDIT_CONFIGS'
BUNDLEUTILS_BUNDLE_DESCRIPTION = 'BUNDLEUTILS_BUNDLE_DESCRIPTION'
BUNDLEUTILS_JENKINS_URL = 'BUNDLEUTILS_JENKINS_URL'
BUNDLEUTILS_USERNAME = 'BUNDLEUTILS_USERNAME'
BUNDLEUTILS_PASSWORD = 'BUNDLEUTILS_PASSWORD'
BUNDLEUTILS_PATH = 'BUNDLEUTILS_PATH'
BUNDLEUTILS_BUNDLE_NAME = 'BUNDLEUTILS_BUNDLE_NAME'
BUNDLEUTILS_BUNDLE_NAME_FROM_PROFILES = 'BUNDLEUTILS_BUNDLE_NAME_FROM_PROFILES'
BUNDLEUTILS_FETCH_TARGET_DIR = 'BUNDLEUTILS_FETCH_TARGET_DIR'
BUNDLEUTILS_MERGE_CONFIG = 'BUNDLEUTILS_MERGE_CONFIG'
BUNDLEUTILS_MERGE_BUNDLES = 'BUNDLEUTILS_MERGE_BUNDLES'
BUNDLEUTILS_MERGE_USE_PARENT = 'BUNDLEUTILS_MERGE_USE_PARENT'
BUNDLEUTILS_MERGE_PREFER_VERSION = 'BUNDLEUTILS_MERGE_PREFER_VERSION'
BUNDLEUTILS_MERGE_OUTDIR = 'BUNDLEUTILS_MERGE_OUTDIR'
BUNDLEUTILS_MERGE_TRANSFORM_PERFORM = 'BUNDLEUTILS_MERGE_TRANSFORM_PERFORM'
BUNDLEUTILS_MERGE_TRANSFORM_SOURCE_DIR = 'BUNDLEUTILS_MERGE_TRANSFORM_SOURCE_DIR'
BUNDLEUTILS_MERGE_TRANSFORM_TARGET_DIR = 'BUNDLEUTILS_MERGE_TRANSFORM_TARGET_DIR'
BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK = 'BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK'
BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR = 'BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR'
# The strategy for handling warnings when fetching the catalog.
# These warning make the yaml purposely invalid so that people cannot simply use the output
# without fixing the issues.
# The options are from the PluginCatalogWarningsStrategy enum below.
# e.g.
# --- There are Beekeeper warnings. This makes the bundle export a "best effort".
# --- Exported plugin catalog and plugins list might be incorrect and might need manual fixing before use.
# --- Pipeline: Groovy Libraries (pipeline-groovy-lib). Version 740.va_2701257fe8d is currently installed but version 727.ve832a_9244dfa_ is recommended for this version of the product.
BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY = 'BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY'
BUNDLEUTILS_FETCH_OFFLINE = 'BUNDLEUTILS_FETCH_OFFLINE'
BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE = 'BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE'
BUNDLEUTILS_PLUGINS_JSON_PATH = 'BUNDLEUTILS_PLUGINS_JSON_PATH'
BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY = 'BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY'
BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY = 'BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY'
BUNDLEUTILS_BUNDLES_DIR = 'BUNDLEUTILS_BUNDLES_DIR'
BUNDLEUTILS_CREDENTIAL_DELETE_SIGN = 'PLEASE_DELETE_ME'
# used to hash the credentials instead of creating environment variables for them
# this will be used in the new audit feature
BUNDLEUTILS_CREDENTIAL_HASH = 'BUNDLEUTILS_CREDENTIAL_HASH'
BUNDLEUTILS_CREDENTIAL_HASH_SEED = 'BUNDLEUTILS_CREDENTIAL_HASH_SEED'

# context object keys
BUNDLE_PROFILES = 'BUNDLE_PROFILES'
ORIGINAL_CWD = 'ORIGINAL_CWD'

# click ctx object keys
ENV_FILE_ARG = 'env_file'
KEYS_TO_CONVERT_TO_SCALARS_ARG = 'keys_to_convert_to_scalars'
INTERACTIVE_ARG = 'interactive'
BUNDLES_DIR_ARG = 'bundles_dir'
CI_VERSION_ARG = 'ci_version'
CI_TYPE_ARG = 'ci_type'
CI_SERVER_HOME_ARG = 'ci_server_home'
CI_MAX_START_TIME_ARG = 'ci_max_start_time'
SOURCE_DIR_ARG = 'source_dir'
SOURCE_BASE_ARG = 'source_base'
EXTERNAL_RBAC_ARG = 'external_rbac'
TARGET_DIR_ARG = 'target_dir'
PLUGIN_JSON_ADDITIONS_ARG = 'plugin_json_additions'
PLUGIN_JSON_URL_ARG = 'plugin_json_url'
PLUGIN_JSON_PATH_ARG = 'plugin_json_path'
PATH_ARG = 'path'
URL_ARG = 'url'
USERNAME_ARG = 'username'
PASSWORD_ARG = 'password'
MERGE_CONFIG_ARG = 'config'
BUNDLES_ARG = 'bundles'
OUTDIR_ARG = 'outdir'

def die(msg):
    logging.error(f"{msg}\n")
    sys.exit(1)

# - 'FAIL' - fail the command if there are warnings
# - 'COMMENT' - add a comment to the yaml with the warnings
class CatalogWarningsStrategy(Enum):
    FAIL = auto()
    COMMENT = auto()

class PluginJsonMergeStrategy(Enum):
    ALL = auto()
    DO_NOTHING = auto()
    ADD_ONLY = auto()
    ADD_DELETE = auto()
    ADD_DELETE_SKIP_PINNED = auto()
    def should_delete(self):
        return self == PluginJsonMergeStrategy.ADD_DELETE or self == PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED
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
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.preserve_quotes = True

    def recursive_sort(obj):
        """Recursively sort dictionary keys to ensure a consistent order."""
        if isinstance(obj, dict):
            return OrderedDict(sorted((k, recursive_sort(v)) for k, v in obj.items()))
        elif isinstance(obj, list):
            return [recursive_sort(i) for i in obj]
        return obj

    ordered_data = recursive_sort(data)
    return printYaml(ordered_data, True)

def generate_collection_uuid(target_dir, yaml_files, output_sorted=None):
    """Generate a stable UUID for a collection of YAML files."""
    yaml = YAML()
    combined_yaml_data = OrderedDict()

    for file in sorted(yaml_files):  # Ensure consistent file order
        file_path = Path(target_dir) / file
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.load(f)
                if data:  # Only merge non-empty files
                    combined_yaml_data[file_path.name] = data  # Use filename as key to preserve structure

    ordered_yaml_str = ordered_yaml_dump(combined_yaml_data)
    yaml_hash = hashlib.sha256(ordered_yaml_str.encode()).hexdigest()
    if output_sorted:
        if not os.path.exists(output_sorted):
            if output_sorted.endswith('.yaml'):
                with open(output_sorted, 'w') as f:
                    f.write('')
            else:
                os.makedirs(output_sorted)
        # if output_sorted is a directory, print each file to a separate file
        if os.path.isdir(output_sorted):
            for file in os.listdir(output_sorted):
                os.remove(os.path.join(output_sorted, file))
            # copy the target_dir bundle.yaml file to the output directory
            target_bundle_yaml = Path(target_dir) / 'bundle.yaml'
            if target_bundle_yaml.exists():
                shutil.copy(target_bundle_yaml, output_sorted)
            # copy other files
            for file_name, data in combined_yaml_data.items():
                with open(os.path.join(output_sorted, file_name), 'w') as f:
                    logging.info(f"Writing {file_name} sorted YAML to {output_sorted}")
                    f.write(ordered_yaml_dump(data))
            # run _update_bundle without the --output-sorted flag
            # to update the bundle.yaml file with the new UUID
            announce(f"Updating the sorted bundle.yaml with UUID: {yaml_hash}")
            _update_bundle(output_sorted)
        else:
            with open(output_sorted, 'w') as f:
                logging.info(f"Writing {yaml_hash} ({uuid.UUID(yaml_hash[:32])}) sorted YAML to {output_sorted}")
                f.write(ordered_yaml_str)
    return str(uuid.UUID(yaml_hash[:32]))  # Convert first 32 chars to UUID format

def get_value_from_enum(value, my_enum):
    try:
        return my_enum[value]
    except KeyError:
        die(f"Invalid value: {value} for {my_enum}. Must be one of {[e.name for e in my_enum]}")

def get_name_from_enum(my_enum):
    return [x.name for x in my_enum]


def common_options(func):
    func = click.option('-l', '--log-level', default=os.environ.get(BUNDLEUTILS_LOG_LEVEL, 'INFO'), help=f'The log level ({BUNDLEUTILS_LOG_LEVEL}).')(func)
    func = click.option('-e', '--env-file', default=os.environ.get(BUNDLEUTILS_ENV, ''), type=click.Path(file_okay=True, dir_okay=False), help=f'Optional bundle profiles file ({BUNDLEUTILS_ENV}).')(func)
    func = click.option('-i', '--interactive', default=False, is_flag=True, help=f'Run in interactive mode.')(func)
    return func

def server_options(func):
    func = click.option('-v', '--ci-version', type=click.STRING, help=f'The version of the CloudBees WAR file.')(func)
    func = click.option('-t', '--ci-type', type=click.STRING, help=f'The type of the CloudBees server.')(func)
    func = click.option('-H', '--ci-server-home', required=False, help=f'Defaults to /tmp/ci_server_home/<ci_type>/<ci_version>.')(func)
    return func

def fetch_options(func):
    func = click.option('-M', '--plugin-json-path', help=f'The path to fetch JSON file from (found at {plugin_json_url_path}).')(func)
    func = click.option('-P', '--path', 'path', type=click.Path(file_okay=True, dir_okay=False), help=f'The path to fetch YAML from ({BUNDLEUTILS_PATH}).')(func)
    func = click.option('-O', '--offline', default=False, is_flag=True, help=f'Save the export and plugin data to <target-dir>-offline ({BUNDLEUTILS_FETCH_OFFLINE}).')(func)
    func = click.option('-U', '--url', 'url', help=f'The URL to fetch YAML from ({BUNDLEUTILS_JENKINS_URL}).')(func)
    func = click.option('-u', '--username', help=f'Username for basic authentication ({BUNDLEUTILS_USERNAME}).')(func)
    func = click.option('-p', '--password', help=f'Password for basic authentication ({BUNDLEUTILS_PASSWORD}).')(func)
    func = click.option('-t', '--target-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory for the YAML documents ({BUNDLEUTILS_FETCH_TARGET_DIR}).')(func)
    func = click.option('-k', '--keys-to-scalars', help=f'Comma-separated list of yaml dict keys to convert to "|" type strings instead of quoted strings, defaults to \'{",".join(default_keys_to_scalars)}\' ({BUNDLEUTILS_KEYS_TO_CONVERT_TO_SCALARS}).')(func)
    return func


def update_plugins_options(func):
    func = click.option('-c', '--cap', default=False, is_flag=True, help=f'Use the envelope.json from the war file to remove CAP plugin dependencies ({BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE}).')(func)
    func = click.option('-j', '--plugins-json-list-strategy', help=f'Strategy for creating list from the plugins json ({BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY}).')(func)
    func = click.option('-J', '--plugins-json-merge-strategy', help=f'Strategy for merging plugins from list into the bundle ({BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY}).')(func)
    func = click.option('-C', '--catalog-warnings-strategy', help=f'Strategy for handling beekeeper warnings in the plugin catalog ({BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY}).')(func)
    return func


def server_options_null_check(ci_version, ci_type, ci_server_home):
    ci_version = null_check(ci_version, CI_VERSION_ARG, BUNDLEUTILS_CI_VERSION)
    ci_type = null_check(ci_type, CI_TYPE_ARG, BUNDLEUTILS_CI_TYPE)
    ci_server_home = null_check(ci_server_home, CI_SERVER_HOME_ARG, BUNDLEUTILS_CI_SERVER_HOME, False)
    return ci_version, ci_type, ci_server_home

def transform_options(func):
    func = click.option('-d', '--dry-run', default=False, is_flag=True, help=f'Print the merged transform config and exit.')(func)
    func = click.option('-S', '--strict', default=False, is_flag=True, help=f'Fail when referencing non-existent files - warn otherwise.')(func)
    func = click.option('-c', '--config', 'configs', type=click.Path(file_okay=True, dir_okay=False), multiple=True, help=f'The transformation config(s).')(func)
    func = click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The source directory for the YAML documents.')(func)
    func = click.option('-t', '--target-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory for the YAML documents. Defaults to the source directory suffixed with -transformed.')(func)
    return func

def _set_env_if_not_set(prefix, env_var, value):
    if not os.environ.get(env_var, ''):
        logging.info(f'{prefix} environment variable: {env_var}={value}')
        os.environ[env_var] = value

def _check_for_env_file(ctx):
    if ctx.obj.get(BUNDLEUTILS_ENV, ''):
        # we have an env file, no need to check for auto vars
        return

    # try to find an env file
    env_file = ''
    if ctx.obj.get(ENV_FILE_ARG):
        env_file = ctx.obj.get(ENV_FILE_ARG)
        logging.debug(f'Using env file from the command line: {env_file}')
    else:
        # if the BUNDLEUTILS_ENV env var is set, use it
        if os.environ.get(BUNDLEUTILS_ENV, ''):
            env_file = os.environ.get(BUNDLEUTILS_ENV)
            if not os.path.exists(env_file):
                die(f'Env var {BUNDLEUTILS_ENV} passed does not exist: {env_file}')
            logging.debug(f'Using env file from environment variable: {env_file}')
        else:
            # search upwards recursively for an env file, max depth of 5
            default_env_file = os.environ.get(BUNDLEUTILS_AUTO_ENV_FILE, default_auto_env_file)
            logging.debug(f'Searching for auto env file {default_env_file} in parent directories')
            auto_env_file_path_dir = os.getcwd()
            for i in range(5):
                if auto_env_file_path_dir == '/':
                    break
                auto_env_file_path = os.path.join(auto_env_file_path_dir, default_env_file)
                logging.debug(f'Checking for env file: {auto_env_file_path}')
                if os.path.exists(auto_env_file_path):
                    logging.debug(f'Auto env file found: {auto_env_file_path}')
                    env_file = auto_env_file_path
                    break
                auto_env_file_path_dir = os.path.dirname(auto_env_file_path_dir)
            if env_file:
                logging.debug(f'Using auto env file: {env_file}')
            else:
                logging.debug(f'No auto env file found')

    if env_file:
        ctx.obj[BUNDLEUTILS_ENV] = env_file
        os.environ[BUNDLEUTILS_ENV] = env_file

        logging.debug(f'Loading config file: {env_file}')
        with open(env_file, 'r') as f:
            bundle_profiles = yaml.load(f)
            # sanity checks
            if not isinstance(bundle_profiles, dict):
                die(f'Invalid bundle profiles file - should be a dict: {env_file}')
            if 'profiles' not in bundle_profiles:
                die(f'Invalid bundle profiles file - should contain a key called "profiles": {env_file}')
            elif not isinstance(bundle_profiles['profiles'], dict):
                die(f'Invalid bundle profiles file - profiles should be a dict: {env_file}')
            if 'bundles' not in bundle_profiles:
                die(f'Invalid bundle profiles file - should contain a key called "bundles": {env_file}')
            elif not isinstance(bundle_profiles['bundles'], dict):
                die(f'Invalid bundle profiles file - bundles should be a dict: {env_file}')
            # set the object in the context
            ctx.obj[BUNDLE_PROFILES] = bundle_profiles
    else:
        ctx.obj[BUNDLEUTILS_ENV] = ''
        logging.debug(f'No env file provided or found')

def _check_cwd_for_bundle_auto_vars(ctx, switch_dirs = True):
    """Check the current working directory for a bundle.yaml file and set the auto vars if found"""
    # no bundle_profiles found, no need to check
    if not ctx.obj.get(BUNDLE_PROFILES, ''):
        logging.debug('No bundle profiles found. No need to check for auto vars')
        return
    # if the cwd contains a file bundle.yaml
    if not os.path.exists('bundle.yaml'):
        logging.debug('No bundle.yaml found in current directory. No need to check for auto vars')
        return

    env_vars = {}
    cwd = os.getcwd()
    if not ctx.obj.get(ORIGINAL_CWD, ''):
        ctx.obj[ORIGINAL_CWD] = cwd

    # if the BUNDLE_PROFILES exists, then the BUNDLEUTILS_ENV must also exist
    auto_env_file_path_dir = os.path.dirname(ctx.obj.get(BUNDLEUTILS_ENV))
    bundle_profiles = ctx.obj.get(BUNDLE_PROFILES)
    bundle_name = _basename(cwd)

    # if the cwd is a subdirectory of auto_env_file_path_dir, create a relative path
    bundle_audit_target_dir = None
    logging.debug(f'Current working directory: {cwd}')
    if switch_dirs:
        logging.debug(f'Switching to the base directory of env file: {auto_env_file_path_dir}')
        os.chdir(auto_env_file_path_dir)
    else:
        logging.debug(f'Not switching directories')

    # if the cwd contains a file bundle.yaml
    adhoc_profile = os.environ.get(BUNDLEUTILS_USE_PROFILE, '')
    bundle_env_vars = {}
    if bundle_name in bundle_profiles['bundles']:
        bundle_env_vars = bundle_profiles['bundles'][bundle_name]
    if adhoc_profile:
        logging.info(f'Found env var {BUNDLEUTILS_USE_PROFILE}: {adhoc_profile}')
        if adhoc_profile in bundle_profiles['profiles']:
            logging.info(f'Using adhoc bundle config for {bundle_name}')
            env_vars = bundle_profiles['profiles'][adhoc_profile]
            for key in [BUNDLEUTILS_CI_VERSION, BUNDLEUTILS_JENKINS_URL]:
                if key in bundle_env_vars:
                    logging.info(f'Adding {key}={bundle_env_vars[key]} from bundle config')
                    env_vars[key] = bundle_env_vars[key]
        else:
            die(f'No bundle profile found for {adhoc_profile}')
    elif bundle_env_vars:
        logging.info(f'Found bundle config for {bundle_name}')
        env_vars = bundle_env_vars
    else:
        logging.info(f'No bundle config found for {bundle_name} and no {BUNDLEUTILS_USE_PROFILE} set')

    # get target dir values
    bundle_target_dir = cwd
    if cwd.startswith(auto_env_file_path_dir):
        bundle_target_dir = os.path.relpath(cwd, auto_env_file_path_dir)
        bundle_audit_target_base_dir = null_check(env_vars.get(BUNDLEUTILS_AUDIT_TARGET_BASE_DIR, ''), 'bundle_audit_target_base_dir', BUNDLEUTILS_AUDIT_TARGET_BASE_DIR, '', False)
        # if the BUNDLEUTILS_AUDIT_TARGET_BASE_DIR is set, use it
        if bundle_audit_target_base_dir:
            bundle_audit_target_dir = os.path.join(bundle_audit_target_base_dir, bundle_target_dir)

    if env_vars:
        # check if the BUNDLEUTILS_ENV_OVERRIDE is set to true, if so, override the env vars
        should_env_vars_override_others = is_truthy(os.environ.get(BUNDLEUTILS_ENV_OVERRIDE, 'false'))
        for key, value in env_vars.items():
            if key not in os.environ:
                logging.info(f'Setting environment variable: {key}={value}')
                os.environ[key] = str(value)
            elif should_env_vars_override_others:
                logging.info(f'Overriding with env, setting: {key}=' + os.environ[key])
            else:
                logging.info(f'Ignoring passed env, setting: {key}={value}')
                os.environ[key] = str(value)
        # set the BUNDLEUTILS_FETCH_TARGET_DIR and BUNDLEUTILS_TRANSFORM_SOURCE_DIR to the default target/docs
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_BUNDLE_NAME, bundle_name)
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_FETCH_TARGET_DIR, f'target/fetched/{bundle_name}')
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_TRANSFORM_SOURCE_DIR, os.environ.get(BUNDLEUTILS_FETCH_TARGET_DIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_TRANSFORM_TARGET_DIR, bundle_target_dir)
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_SETUP_SOURCE_DIR, os.environ.get(BUNDLEUTILS_TRANSFORM_TARGET_DIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_VALIDATE_SOURCE_DIR, os.environ.get(BUNDLEUTILS_TRANSFORM_TARGET_DIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_MERGE_OUTDIR, f'target/merged/{bundle_name}')
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_MERGE_TRANSFORM_SOURCE_DIR, os.environ.get(BUNDLEUTILS_MERGE_OUTDIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_MERGE_TRANSFORM_TARGET_DIR, f'target/expected/{bundle_name}')
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR, bundle_target_dir)
        # special case for audit, set the source dir to the fetch target dir and the target dir to the audit target dir
        if bundle_audit_target_dir is not None:
            _set_env_if_not_set('AUTOSET', BUNDLEUTILS_AUDIT_SOURCE_DIR, os.environ.get(BUNDLEUTILS_FETCH_TARGET_DIR))
            _set_env_if_not_set('AUTOSET', BUNDLEUTILS_AUDIT_TARGET_DIR, bundle_audit_target_dir)
        # loop through the env vars and replace any placeholders
        placeholder_re = re.compile(r'\$\{([^\}]+)\}')
        for key, value in os.environ.items():
            if key.startswith('BUNDLEUTILS_'):
                new_value = placeholder_re.sub(lambda m: os.environ.get(m.group(1), ''), value)
                if new_value != value:
                    logging.info(f'Replacing {key}={value} with {new_value}')
                    os.environ[key] = new_value


def is_truthy(value):
    return value.lower() in ['true', '1', 't', 'y', 'yes']

def set_logging(ctx, switch_dirs = True):
    _check_for_env_file(ctx)
    _check_cwd_for_bundle_auto_vars(ctx, switch_dirs)

@click.group(invoke_without_command=True)
@common_options
@click.pass_context
def bundleutils(ctx, log_level, env_file, interactive):
    """A tool to fetch and transform YAML documents."""
    ctx.ensure_object(dict)
    ctx.max_content_width=120
    ctx.obj[ENV_FILE_ARG] = env_file
    ctx.obj[INTERACTIVE_ARG] = interactive
    if not ctx.obj.get(BUNDLEUTILS_LOG_LEVEL, ''):
        ctx.obj[BUNDLEUTILS_LOG_LEVEL] = log_level
        logging.getLogger().setLevel(log_level)
        logging.debug(f"Set log level to: {log_level}")
    if not ctx.obj.get(ORIGINAL_CWD, ''):
        ctx.obj[ORIGINAL_CWD] = os.getcwd()
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

def yaml2dict(yamlFile):
    dict_res = {}
    with open(yamlFile, 'r') as fp:
        datax = yaml.load_all(fp)
        for data in datax:
            for key, value in data.items():
                dict_res[key] = value
    return dict_res

def compare_func(x, y, level=None):
    try:
        return x['id'] == y['id']
    except Exception:
        raise CannotCompare() from None

def lookup_url_and_version(url, ci_version, default_url = '', default_ci_version = ''):
    url = lookup_url(url, default_url)
    ci_version = null_check(ci_version, CI_VERSION_ARG, BUNDLEUTILS_CI_VERSION, False, default_ci_version)
    if not ci_version:
        whoami_url = f'{url}/whoAmI/api/json?tree=authenticated'
        try:
            response = requests.get(whoami_url, timeout=5)
            if response.status_code == 200:
                # get headers from the whoami_url
                headers = response.headers
                logging.debug(f"Headers: {headers}")
                # get the x-jenkins header ignoring case and removing any carriage returns
                ci_version = headers.get('x-jenkins', headers.get('X-Jenkins', '')).replace('\r', '')
                logging.debug(f"Version: {ci_version} (taken from remote)")
            else:
                die(f"URL {url} returned a non-OK status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            die(f"URL {url} is not reachable. Reason: {e}")
    else:
        logging.debug(f"Version: {ci_version} (taken from command line)")
    return url, ci_version

def lookup_url(url, default_url = '', mandatory = True):
    url_env = 'JENKINS_URL'
    if os.environ.get(BUNDLEUTILS_JENKINS_URL):
        url_env = BUNDLEUTILS_JENKINS_URL
    return null_check(url, URL_ARG, url_env, mandatory, default_url)

@bundleutils.command()
@click.pass_context
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be bootstrapped.')
@click.option('-S', '--source-base', type=click.Path(file_okay=False, dir_okay=True), help=f'Specify parent dir of source-dir, bundle name taken from URL.')
@click.option('-U', '--url', help=f'The controller URL to bootstrap (JENKINS_URL).')
@click.option('-v', '--ci-version', type=click.STRING, help=f'Optional version (taken from the remote instance otherwise).')
def delete(ctx, source_dir, source_base, url, ci_version):
    """
    Delete a bundle source dir and the corresponding entry in bundle-profiles.yaml
    """
    _check_for_env_file(ctx)
    # no bundle_profiles found, no need to check
    if not ctx.obj.get(BUNDLE_PROFILES, ''):
        logging.debug('No bundle profiles found. Nothing to add the bundle to.')
        return
    # source_dir and source_base are mutually exclusive but we need one of them
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR, False, '')
    source_base = null_check(source_base, SOURCE_BASE_ARG, BUNDLEUTILS_BOOTSTRAP_SOURCE_BASE, False, '')
    if source_dir and source_base:
        die('source-dir and source-base are mutually exclusive')
    elif source_base:
        url = lookup_url(url)
        bundle_name = _extract_name_from_url(url)
        source_dir = os.path.join(source_base, bundle_name)
        logging.info(f"Using source-dir: {source_dir} (derived from source-base and URL)")
    elif source_dir:
        logging.info(f"Using source-dir: {source_dir}")
    else:
        die('Either source-dir or source-base must be provided')
    # bundle_profiles yaml
    bundle_profiles = ctx.obj.get(BUNDLE_PROFILES)
    bundle_name = _basename(source_dir)
    if bundle_name in bundle_profiles['bundles']:
        logging.info(f'Deleting bundle {bundle_name} entry in the bundle-profiles.yaml')
        del bundle_profiles['bundles'][bundle_name]
    else:
        logging.info(f'No bundle config found for {bundle_name}. Nothing to delete')

    if not os.path.exists(source_dir):
        logging.info(f"Bundle {bundle_name} does not exist. Nothing to delete")
    else:
        logging.info(f'Deleting bundle {bundle_name} source directory')
        shutil.rmtree(source_dir)

    # Loop through the profiles and reapply anchors dynamically since they get lost when loading the file
    for key, value in bundle_profiles['profiles'].items():
        if isinstance(value, dict):
            value.yaml_set_anchor(key, always_dump=True)
    # write the updated file
    with open(ctx.obj.get(BUNDLEUTILS_ENV), 'w') as ofp:
        yaml.dump(bundle_profiles, ofp)

@bundleutils.command()
@click.pass_context
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be bootstrapped.')
@click.option('-S', '--source-base', type=click.Path(file_okay=False, dir_okay=True), help=f'Specify parent dir of source-dir, bundle name taken from URL.')
@click.option('-p', '--profile', help=f'The bundle profile to use.')
@click.option('-u', '--update', help=f'Should the bundle be updated if present.')
@click.option('-U', '--url', help=f'The controller URL to bootstrap (JENKINS_URL).')
@click.option('-v', '--ci-version', type=click.STRING, help=f'Optional version (taken from the remote instance otherwise).')
def bootstrap(ctx, source_dir, source_base, profile, update, url, ci_version):
    """
    Bootstrap a bundle.
    """
    _check_for_env_file(ctx)
    # no bundle_profiles found, no need to check
    if not ctx.obj.get(BUNDLE_PROFILES, ''):
        logging.debug('No bundle profiles found. Nothing to add the bundle to.')
        return
    # source_dir and source_base are mutually exclusive but we need one of them
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR, False, '')
    source_base = null_check(source_base, SOURCE_BASE_ARG, BUNDLEUTILS_BOOTSTRAP_SOURCE_BASE, False, '')
    if source_dir and source_base:
        die('source-dir and source-base are mutually exclusive')
    elif source_base:
        url = lookup_url(url)
        bundle_name = _extract_name_from_url(url)
        source_dir = os.path.join(source_base, bundle_name)
        logging.info(f"Using source-dir: {source_dir} (derived from source-base and URL)")
    elif source_dir:
        logging.info(f"Using source-dir: {source_dir}")
    else:
        die('Either source-dir or source-base must be provided')

    bootstrap_profile = null_check(profile, 'profile', BUNDLEUTILS_BOOTSTRAP_PROFILE)
    bootstrap_update = null_check(update, 'update', BUNDLEUTILS_BOOTSTRAP_UPDATE, False, 'false')
    if bootstrap_profile:
        bundle_profiles = ctx.obj.get(BUNDLE_PROFILES)
        bundle_name = _basename(source_dir)
        if bootstrap_profile in bundle_profiles['profiles']:
            default_url = ''
            default_ci_version = ''
            if bundle_name in bundle_profiles['bundles']:
                if bootstrap_update in ['true', '1', 't', 'y', 'yes']:
                    logging.info(f'The bundle config for {bundle_name} already exists. Updating it.')
                    if ctx.obj.get(INTERACTIVE_ARG):
                        default_url = bundle_profiles['bundles'][bundle_name].get(BUNDLEUTILS_JENKINS_URL, '')
                        default_ci_version = bundle_profiles['bundles'][bundle_name].get(BUNDLEUTILS_CI_VERSION, '')
                else:
                    die(f'The bundle config for {bundle_name} already exists. Please check, then either use {BUNDLEUTILS_BOOTSTRAP_UPDATE} or remove it first.')
            else:
                logging.info(f'No bundle config found for {bundle_name}. Adding it to the bundles')
            bundle_yaml = os.path.join(source_dir, 'bundle.yaml')
            url, ci_version = lookup_url_and_version(url, ci_version, default_url, default_ci_version)
            if not os.path.exists(bundle_yaml):
                logging.info(f"Creating an empty {bundle_yaml}")
                os.makedirs(source_dir)
                with open(bundle_yaml, 'w') as file:
                    file.write('')
            else:
                logging.info(f"The bundle yaml already exists {bundle_yaml}")

            # open for reading
            with open(ctx.obj.get(BUNDLEUTILS_ENV)) as ifp:
                data = yaml.load(ifp)
            # Loop through the profiles and reapply anchors dynamically since they get lost when loading the file
            for key, value in data['profiles'].items():
                if isinstance(value, dict):
                    value.yaml_set_anchor(key, always_dump=True)
            # Create a new bundle entry
            upd = CommentedMap()
            upd.add_yaml_merge([(0, data['profiles'][bootstrap_profile])])
            data['bundles'][bundle_name] = upd
            data['bundles'][bundle_name]['BUNDLEUTILS_JENKINS_URL'] = f"{url}"
            data['bundles'][bundle_name]['BUNDLEUTILS_CI_VERSION'] = f"{ci_version}"
            # write the updated file
            with open(ctx.obj.get(BUNDLEUTILS_ENV), 'w') as ofp:
                yaml.dump(data, ofp)
            logging.info(f"Added/updated bundle {bundle_name} with profile {bootstrap_profile}, URL {url}, and version {ci_version}")
        else:
            die(f'No bundle profile found for {bootstrap_profile}')

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
        click.echo('-' * 120)
        click.echo(command.get_help(ctx.parent).replace('Usage: bundleutils', f'Usage: bundleutils {command.name}'))

@bundleutils.command()
@server_options
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be validated (startup will use the plugins from here).')
@click.option('-T', '--ci-bundle-template', type=click.Path(file_okay=False, dir_okay=True), required=False, help=f'Path to a template bundle used to start the test server (defaults to in-built tempalte).')
@click.option('-f', '--force', default=False, is_flag=True, help=f'Force download of the WAR file even if exists.')
@click.pass_context
def ci_setup(ctx, ci_version, ci_type, ci_server_home, source_dir, ci_bundle_template, force):
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
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_SETUP_SOURCE_DIR)
    source_dir = os.path.normpath(source_dir)
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    # parse the source directory bundle.yaml file and copy the files under the plugins and catalog keys to the target_jenkins_home_casc_startup_bundle directory
    bundle_yaml = os.path.join(source_dir, 'bundle.yaml')
    plugin_files = [bundle_yaml]
    with open(bundle_yaml, 'r') as file:
        bundle_yaml = yaml.load(file)
        for key in ['plugins', 'catalog']:
            # list paths to all entries under bundle_yaml.plugins
            if key in bundle_yaml and isinstance(bundle_yaml[key], list):
                for plugin_file in bundle_yaml[key]:
                    plugin_files.append(os.path.join(source_dir, plugin_file))
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.get_war(force)
    jenkins_manager.create_startup_bundle(plugin_files, ci_bundle_template)
    _update_bundle(jenkins_manager.target_jenkins_home_casc_startup_bundle)

@bundleutils.command()
@click.option('-m', '--config', type=click.Path(file_okay=True, dir_okay=False), help=f'An optional custom merge config file if needed.')
@click.option('-f', '--files', multiple=True, type=click.Path(file_okay=True, dir_okay=False), help=f'The files to be merged.')
@click.option('-o', '--outfile', type=click.Path(file_okay=True, dir_okay=False), help=f'The target for the merged file.')
@click.pass_context
def merge_yamls(ctx, config, files, outfile = None):
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
        logging.warning(f"Merging only makes sense with two files. Returning the first file.")
    # merge the files sequentially using the last result as the base
    output = merger.merge_yaml_files(files)
    if not outfile:
        yaml.dump(output, sys.stdout)
    else:
        with open(outfile, "w") as f:
            yaml.dump(output, f)

def _collect_parents(current_bundle, bundles):
    # get the optional parent key from the bundle.yaml
    bundle_yaml = os.path.join(current_bundle, 'bundle.yaml')
    if not os.path.exists(bundle_yaml):
        die(f"Bundle file '{bundle_yaml}' does not exist")
    with open(bundle_yaml, 'r') as file:
        bundle_yaml = yaml.load(file)
        if 'parent' in bundle_yaml:
            parent = bundle_yaml['parent']
            if parent in bundles:
                die(f"Bundle '{parent}' cannot be a parent of itself")
            parent_dir = os.path.join(os.path.dirname(current_bundle), parent)
            if not os.path.exists(parent_dir):
                die(f"Parent bundle '{parent}' does not exist")
            bundles.insert(0, parent_dir)
            return _collect_parents(parent_dir, bundles)
    return bundles

def _merge_bundles(bundles, use_parent, outdir, config, api_version = None):
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

    # handle the BUNDLEUTILS_MERGE_PREFER_VERSION env var
    prefer_version = is_truthy(os.environ.get(BUNDLEUTILS_MERGE_PREFER_VERSION, 'false'))
    if prefer_version:
        current_version = os.environ.get(BUNDLEUTILS_CI_VERSION, '')
        if not current_version:
            die(f"Cannot prefer version without a current version. Please set {BUNDLEUTILS_CI_VERSION}")
        new_bundles = []
        for bundle_dir in bundles:
            # say the bundle_dir is snippets/mybundle and current_version is 1.1.2, check if snippets/mybundle-1.1.2 exists and use it if it does
            versioned_bundle_dir = f"{bundle_dir}-{current_version}"
            logging.info(f"Checking for versioned bundle directory: {versioned_bundle_dir}")
            if os.path.exists(versioned_bundle_dir):
                logging.info(f"Using versioned bundle directory: {versioned_bundle_dir}")
                new_bundles.append(versioned_bundle_dir)
            else:
                if not os.path.exists(bundle_dir):
                    die(f"Bundle directory '{bundle_dir}' does not exist")
                new_bundles.append(bundle_dir)
        bundles = new_bundles

    merger = YAMLMerger(merge_configs)  # Merge lists of dicts by 'name' field
    # ensure at least two files are provided
    if len(bundles) < 1:
        die(f"Please provide at least one bundle to merge")

    # ensure the outdir and a bundle.yaml exist
    if outdir:
        if not os.path.exists(outdir):
            os.makedirs(outdir)
        out_bundle_yaml = os.path.join(outdir, 'bundle.yaml')
        last_bundle_yaml = os.path.join(bundles[-1], 'bundle.yaml')
        if not api_version:
            if os.path.exists(last_bundle_yaml):
                # get the apiVersion and kind from the last bundle.yaml
                last_bundle_yaml_dict = yaml2dict(last_bundle_yaml)
                if 'apiVersion' in last_bundle_yaml_dict:
                    api_version = last_bundle_yaml_dict['apiVersion']
                else:
                    logging.warning(f"Bundle file '{last_bundle_yaml}' does not contain an apiVersion. Using default apiVersion: {default_bundle_api_version}")
                    api_version = default_bundle_api_version
            elif os.environ.get(BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR):
                # get the apiVersion from the source directory
                source_dir = os.environ.get(BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR)
                source_bundle_yaml = os.path.join(source_dir, 'bundle.yaml')
                if os.path.exists(source_bundle_yaml):
                    source_bundle_yaml_dict = yaml2dict(source_bundle_yaml)
                    if 'apiVersion' in source_bundle_yaml_dict:
                        api_version = source_bundle_yaml_dict['apiVersion']
                    else:
                        logging.warning(f"Bundle file '{source_bundle_yaml}' does not contain an apiVersion. Using default apiVersion: {default_bundle_api_version}")
                        api_version = default_bundle_api_version
                else:
                    logging.warning(f"Bundle file '{source_bundle_yaml}' does not exist. Using default apiVersion: {default_bundle_api_version}")
                    api_version = default_bundle_api_version
            else:
                logging.debug(f"Bundle file '{last_bundle_yaml}' does not exist. Using default apiVersion: {api_version}")
                api_version = default_bundle_api_version

        with open(out_bundle_yaml, "w") as f:
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
        if section == 'plugins':
            output['plugins'] = sorted(output['plugins'], key=lambda x: x['id'])
        if not outdir:
            print(f"# {section}.yaml")
            yaml.dump(output, sys.stdout)
        else:
            out_section_yaml = os.path.join(outdir, section_file)
            with open(out_section_yaml, "w") as f:
                logging.info(f"Writing section: {section} to {out_section_yaml}")
                yaml.dump(output, f)
            _update_bundle(outdir)

@bundleutils.command()
@click.option('-S', '--strict', default=False, is_flag=True, help=f'Fail when referencing non-existent files - warn otherwise.')
@click.option('-m', '--config', type=click.Path(file_okay=True, dir_okay=False), help=f'An optional custom merge config file if needed.')
@click.option('-b', '--bundles', multiple=True, type=click.Path(file_okay=False, dir_okay=True, exists=True), help=f'The bundles to be rendered.')
@click.option('-p', '--use-parent', default=False, is_flag=True, help=f'Optionally use the (legacy) parent key to work out which bundles to merge.')
@click.option('-o', '--outdir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target for the merged bundle.')
@click.option('-a', '--api-version', help=f'Optional apiVersion. Defaults to {default_bundle_api_version}')
@click.option('-t', '--transform', default=False, is_flag=True, help=f'Optionally transform using the transformation configs ({BUNDLEUTILS_MERGE_TRANSFORM_PERFORM}).')
@click.option('-d', '--diffcheck', default=False, is_flag=True, help=f'Optionally perform bundleutils diff against the original source bundle and expected bundle ({BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK}).')
@click.pass_context
def merge_bundles(ctx, strict, config, bundles, use_parent, outdir, transform, diffcheck, api_version):
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

    \b
    Prefer versioned directories (env: BUNDLEUTILS_MERGE_PREFER_VERSION):
    - listing "-b snippets/bootstrap" will look for "snippets/bootstrap-2.492.1.3" if the current version is 2.492.1.3

    \b
    Optional features:
    - transform the merged bundle using the transformation configs
        (BUNDLEUTILS_TRANSFORM_CONFIGS and BUNDLEUTILS_TRANSFORM_SOURCE_DIR needed for this)
    - perform a diff check against the source bundle and the transformed bundle
        (BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR needed for this)
    """
    set_logging(ctx)

    config = null_check(config, MERGE_CONFIG_ARG, BUNDLEUTILS_MERGE_CONFIG, False, '')
    bundles = null_check(bundles, BUNDLES_ARG, BUNDLEUTILS_MERGE_BUNDLES, False, '')
    use_parent = null_check(use_parent, 'use_parent', BUNDLEUTILS_MERGE_USE_PARENT, False, '')
    outdir = null_check(outdir, OUTDIR_ARG, BUNDLEUTILS_MERGE_OUTDIR, False, '')

    transform = null_check(transform, 'transform', BUNDLEUTILS_MERGE_TRANSFORM_PERFORM, False, '')
    if transform:
        logging.debug(f"Transforming detected. Looking for transform options")
        transform_outdir = null_check('', 'transform_outdir', BUNDLEUTILS_MERGE_TRANSFORM_TARGET_DIR)
        transform_srcdir = null_check(outdir, OUTDIR_ARG, BUNDLEUTILS_MERGE_TRANSFORM_SOURCE_DIR)
        transform_configs = null_check('', 'configs', BUNDLEUTILS_TRANSFORM_CONFIGS)

    diffcheck = null_check(diffcheck, 'diffcheck', BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK, False, '')
    if diffcheck:
        logging.debug(f"Diffcheck detected. Looking for diffcheck options")
        diffcheck_source_bundle = null_check('', 'diffcheck_source_bundle', BUNDLEUTILS_MERGE_TRANSFORM_DIFFCHECK_SOURCE_DIR)
    # sanity check
    if transform:
        if transform_outdir and not outdir:
            die(f"Cannot perform transform without specifying outdir")
        if diffcheck and not transform_outdir:
            die(f"Cannot perform diffcheck without specifying transform_outdir")
    if diffcheck and not diffcheck_source_bundle:
            die(f"Cannot perform diffcheck without specifying diffcheck_source_bundle")

    if isinstance(bundles, str):
        bundles = bundles.split()

    _merge_bundles(bundles, use_parent, outdir, config, api_version)

    if transform:
        announce(f"Performing transform on merged bundle from {transform_srcdir} to {transform_outdir}")
        _transform(transform_configs, transform_srcdir, transform_outdir)
    if diffcheck:
        announce("Performing diffcheck on transformed bundle")
        diff_dirs(diffcheck_source_bundle, transform_outdir)

def announce(string):
    logging.info(f"Announcing...\n{'*' * 80}\n{string}\n{'*' * 80}")

@bundleutils.command()
@server_options
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be validated.')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help=f'Do not fail if warnings are found.')
@click.option('-r', '--external-rbac', type=click.Path(file_okay=True, dir_okay=False), help=f'Path to an external rbac.yaml from an Operations Center bundle.')
@click.pass_context
def ci_validate(ctx, ci_version, ci_type, ci_server_home, source_dir, ignore_warnings, external_rbac):
    """Validate bundle against controller started with ci-start."""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_VALIDATE_SOURCE_DIR)
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    logging.debug(f"Server URL: {server_url}, Username: {username}, Password: {password}")
    _validate(server_url, username, password, source_dir, ignore_warnings, external_rbac)

@bundleutils.command()
@server_options
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle of the plugins to be sanitized.')
@click.option('-p', '--pin-plugins', default=False, is_flag=True, help=f'Add versions to 3rd party plugins (only available for apiVersion 2).')
@click.option('-c', '--custom-url', help=f'Add a custom URL, e.g. http://plugins-repo/plugins/PNAME/PVERSION/PNAME.hpi')
@click.pass_context
def ci_sanitize_plugins(ctx, ci_version, ci_type, ci_server_home, source_dir, pin_plugins, custom_url):
    """Sanitizes plugins (needs ci-start)."""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_TRANSFORM_TARGET_DIR)
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    logging.debug(f"Server URL: {server_url}, Username: {username}, Password: {password}")

    # read the plugins.yaml file from the source directory
    plugins_file = os.path.join(source_dir, 'plugins.yaml')
    if not os.path.exists(plugins_file):
        die(f"Plugins file '{plugins_file}' does not exist")
    with open(plugins_file, 'r') as f:
        plugins_data = yaml.load(f)  # Load the existing data

    envelope_json = jenkins_manager.get_envelope_json()
    envelope_json = json.loads(envelope_json)

    plugin_json_url = server_url + plugin_json_url_path
    response_text = call_jenkins_api(plugin_json_url, username, password)
    data = json.loads(response_text)

    installed_plugins = {}
    envelope_plugins = {}
    bootstrap_plugins = {}
    for plugin_id, plugin_info in envelope_json['plugins'].items():
        if plugin_info.get('scope') == 'bootstrap':
            logging.debug(f"SANITIZE PLUGINS -> registering bootstrap: {plugin_id}")
            bootstrap_plugins[plugin_id] = plugin_info
        else:
            logging.debug(f"SANITIZE PLUGINS -> registering non-bootstrap: {plugin_id}")
            envelope_plugins[plugin_id] = plugin_info

    for installed_plugin in data['plugins']:
        installed_plugins[installed_plugin['shortName']] = installed_plugin

    # Check if 'plugins' key exists and it's a list
    if 'plugins' in plugins_data and isinstance(plugins_data['plugins'], list):
        updated_plugins = []
        for plugin in plugins_data['plugins']:
            if plugin['id'] in envelope_plugins.keys():
                logging.info(f"SANITIZE PLUGINS -> ignoring bundled: {plugin['id']}")
                updated_plugins.append(plugin)
            elif plugin['id'] in bootstrap_plugins.keys():
                logging.info(f"SANITIZE PLUGINS -> removing bootstrap: {plugin['id']}")
            else:
                if custom_url:
                    # remove the version from the plugin
                    plugin.pop('version', None)
                    plugin['url'] = custom_url.replace('PNAME', plugin['id']).replace('PVERSION', installed_plugins[plugin['id']]['version']).strip()
                    logging.info(f"SANITIZE PLUGINS -> adding URL to: {plugin['id']} ({plugin['url']})")
                    updated_plugins.append(plugin)
                elif pin_plugins:
                    if plugin['id'] in installed_plugins:
                        # remove the url from the plugin
                        plugin.pop('url', None)
                        plugin['version'] = installed_plugins[plugin['id']]['version']
                        logging.info(f"SANITIZE PLUGINS -> adding version to : {plugin['id']} ({plugin['version']})")
                        updated_plugins.append(plugin)
                    else:
                        logging.warning(f"SANITIZE PLUGINS -> no version found for: {plugin['id']}")
                else:
                    logging.info(f"SANITIZE PLUGINS -> not pinning: {plugin['id']}")
                    updated_plugins.append(plugin)
        plugins_data['plugins'] = updated_plugins
    with open(plugins_file, 'w') as f:
        yaml.dump(plugins_data, f)  # Write the updated data back to the file
    _update_bundle(source_dir)

@bundleutils.command()
@server_options
@click.option('-M', '--ci-max-start-time', default=120, envvar=BUNDLEUTILS_CI_MAX_START_TIME, show_envvar=True, required=False, type=click.INT, help=f'Max minutes to start.')
@click.pass_context
def ci_start(ctx, ci_version, ci_type, ci_server_home, ci_max_start_time):
    """Start CloudBees Server"""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.start_server(ci_max_start_time)

@bundleutils.command()
@server_options
@click.pass_context
def ci_stop(ctx, ci_version, ci_type, ci_server_home):
    """Stop CloudBees Server"""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.stop_server()

@bundleutils.command()
@click.option('-s', '--sources', multiple=True, type=click.Path(file_okay=True, dir_okay=True, exists=True), help=f'The directories or files to be diffed.')
@click.pass_context
def diff(ctx, sources):
    """Diff two YAML directories or files."""
    set_logging(ctx, False)
    diff_detected = False
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

@bundleutils.command()
@click.option('-m', '--config', type=click.Path(file_okay=True, dir_okay=False), help=f'An optional custom merge config file if needed.')
@click.option('-s', '--sources', multiple=True, type=click.Path(file_okay=False, dir_okay=True, exists=True), help=f'The bundles to be diffed.')
@click.option('-a', '--api-version', help=f'Optional apiVersion in case bundle does not contain a bundle.yaml. Defaults to {default_bundle_api_version}')
@click.pass_context
def diff_merged(ctx, config, sources, api_version):
    """Diff two bundle directories by temporarily merging both before the diff."""
    set_logging(ctx, False)
    diff_detected = False
    # if src1 is a directory, ensure src2 is also directory
    if sources and len(sources) == 2:
        src1 = sources[0]
        src2 = sources[1]
    else:
        die("Please provide two bundle directories")

    if os.path.isdir(src1) and os.path.isdir(src2):
        # create a temporary directory to store the merged bundle
        with tempfile.TemporaryDirectory() as temp_dir:
            merged1 = os.path.join(temp_dir, 'merged1', 'dummy')
            merged2 = os.path.join(temp_dir, 'merged2', 'dummy')
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

@bundleutils.command()
@click.pass_context
def config(ctx):
    """List evaluated config based on cwd and env file."""

    set_logging(ctx)
    # loop through all the environment variables, sorted alphabetically, starting with BUNDLEUTILS_ and print them as a single multiline string
    logging.info("Evaluated configuration:")
    lines = []
    for key, value in sorted(os.environ.items()):
        if key.startswith('BUNDLEUTILS_'):
            # if the key is a password, mask it
            if 'PASSWORD' in key:
                value = '*' * len(value)
            lines.append(f'{key}={value}')
    click.echo('\n'.join(lines))

@bundleutils.command()
def version():
    """Show the app version."""
    try:
        package_name = 'bundleutilspkg'
        pkg_metadata = metadata(package_name)
        click.echo(f"{pkg_metadata['Version']}")
    except PackageNotFoundError:
        try:
            click.echo(__version__)
        except AttributeError:
            click.echo("Cannot determine version.")
        click.echo("Package is not installed. Please ensure it's built and installed correctly.")

@bundleutils.command()
@click.option('-u', '--url', help=f'The URL to extract the controller name from.')
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
    name = _extract_name_from_url(url)
    click.echo(name)

def _extract_name_from_url(url):
    url = lookup_url(url)
    parsed = urlparse(url)
    # Check if the URL has a path
    if parsed.path and parsed.path != '/':
        return parsed.path.rstrip('/').split('/')[-1]
    # Otherwise, extract the first subdomain
    else:
        subdomain = parsed.netloc.split('.')[0]
        return subdomain

@bundleutils.command()
@click.option('-U', '--url', help=f'The controller URL to test for (JENKINS_URL).')
@click.option('-v', '--ci-version', type=click.STRING, help=f'Optional version (taken from the remote instance otherwise).')
@click.option('-b', '--bundles-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The directory containing the bundles.')
@click.pass_context
def find_bundle_by_url(ctx, url, ci_version, bundles_dir):
    """
    Find a bundle by Jenkins URL and CI Version.

    Use -v '.*' to match any version.
    """
    set_logging(ctx)
    if not ctx.obj.get(BUNDLE_PROFILES, ''):  # if no bundle profiles are found, exit
        logging.error("No bundle profiles found. Exiting.")
        return
    bundles_dir = null_check(bundles_dir, BUNDLES_DIR_ARG, BUNDLEUTILS_BUNDLES_DIR, False, ctx.obj.get(ORIGINAL_CWD))
    url, ci_version = lookup_url_and_version(url, ci_version)
    # search the profiles for a bundle with the given URL and version
    my_bundle = None
    bundle_profiles = ctx.obj.get(BUNDLE_PROFILES)
    for bundle_name, bundle_env_vars in bundle_profiles['bundles'].items():
        if bundle_env_vars.get(BUNDLEUTILS_JENKINS_URL, '').strip().rstrip('/') == url.strip().rstrip('/') and re.match(ci_version, bundle_env_vars.get(BUNDLEUTILS_CI_VERSION, '')):
            logging.debug(f"Found bundle: {bundle_name}. Checking for bundle.yaml in {bundles_dir}")
            bundles_found = []
            for bundle_found in glob.iglob(f'{bundles_dir}/**/{bundle_name}/bundle.yaml', recursive=True):
                logging.debug(f"Found bundle.yaml: {bundle_found}")
                bundles_found.append(bundle_found)
                if my_bundle:
                    # exit with exit code 1 and text message if a second bundle is found
                    die(f"Multiple bundles found with the name '{bundle_found}'")

            if len(bundles_found) > 1:
                die(f"Multiple bundles found: {bundles_found}")
            if len(bundles_found) == 1:
                # echo the parent directory of the bundle.yaml file
                click.echo(os.path.dirname(bundles_found[0]))
                my_bundle = bundle_name
    if not my_bundle:
        die(f"No bundle found for URL {url} and version {ci_version}")

# add completion command which takes the shell as an argument
# shell can only be bash, fish, or zsh
@bundleutils.command()
@click.option('-s', '--shell', required=True, type=click.Choice(['bash', 'fish', 'zsh']), help=f'The shell to generate completion script for.')
@click.pass_context
def completion(ctx, shell):
    """Print the shell completion script"""
    ctx.ensure_object(dict)
    # run process 'echo "$(_BUNDLEUTILS_COMPLETE=bash_source bundleutils)"'
    click.echo("Run either of the following commands to enable completion:")
    click.echo(f'  1. eval "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})"')
    click.echo(f'  2. echo "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})" > {script_name}-complete.{shell}')
    click.echo(f'     source {script_name}-complete.{shell}')

@click.pass_context
def null_check(ctx, obj, obj_name, obj_env_var=None, mandatory=True, default=''):
    """Check if the object is None and set it to the env var or default if mandatory"""
    if not obj:
        if obj_env_var:
            obj = os.environ.get(obj_env_var, '')
            if not obj:
                if default:
                    obj = default
                if mandatory and ctx.obj.get(INTERACTIVE_ARG):
                    if obj_env_var:
                        msg = f'Please provide the {obj_name} or set the {obj_env_var}'
                    else:
                        msg = f'Please provide the {obj_name}'
                    if obj:
                        obj = click.prompt(msg, default=obj)
                    else:
                        obj = click.prompt(msg)
                if mandatory and not obj:
                    die(f'No {obj_name} option provided and no {obj_env_var} set')
    # mask password or token
    obj_str = obj
    if 'password' in obj_name or 'token' in obj_name:
        obj_str = '*******'
    logging.debug(f'Setting ctx - > {obj_name}: {obj_str}')
    # if the object_name already exists in the context and if different, warn the user
    if obj_name in ctx.obj and ctx.obj[obj_name] != obj:
        logging.warning(f'Overriding {obj_name} from {ctx.obj[obj_name]} to {obj_str}')
    ctx.obj[obj_name] = obj
    return obj

@bundleutils.command()
@click.option('-U', '--url', help=f'The controller URL to validate agianst ({BUNDLEUTILS_JENKINS_URL}).')
@click.option('-u', '--username', help=f'Username for basic authentication ({BUNDLEUTILS_USERNAME}).')
@click.option('-p', '--password', help=f'Password for basic authentication ({BUNDLEUTILS_PASSWORD}).')
@click.option('-s', '--source-dir', required=True, type=click.Path(file_okay=False, dir_okay=True), help=f'The source directory for the YAML documents ({BUNDLEUTILS_VALIDATE_SOURCE_DIR}).')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help=f'Do not fail if warnings are found.')
@click.option('-r', '--external-rbac', type=click.Path(file_okay=True, dir_okay=False), help=f'Path to an external rbac.yaml from an Operations Center bundle.')
@click.pass_context
def validate(ctx, url, username, password, source_dir, ignore_warnings, external_rbac):
    """Validate bundle in source dir against URL."""
    set_logging(ctx)
    _validate(url, username, password, source_dir, ignore_warnings, external_rbac)

def _validate(url, username, password, source_dir, ignore_warnings, external_rbac):
    username = null_check(username, 'username', BUNDLEUTILS_USERNAME)
    password = null_check(password, 'password', BUNDLEUTILS_PASSWORD)
    source_dir = null_check(source_dir, 'source directory', BUNDLEUTILS_VALIDATE_SOURCE_DIR)
    external_rbac = null_check(external_rbac, EXTERNAL_RBAC_ARG, BUNDLEUTILS_VALIDATE_EXTERNAL_RBAC, False)
    url = lookup_url(url)

    if external_rbac:
        if not os.path.exists(external_rbac):
            die(f"RBAC configuration file not found in {external_rbac}")
        logging.info(f"Using RBAC from {external_rbac}")

    # if the url does end with /casc-bundle-mgnt/casc-bundle-validate, append it
    if validate_url_path not in url:
        url = url + validate_url_path

    # fetch the YAML from the URL
    headers = { 'Content-Type': 'application/zip' }
    if username and password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')

    # create a temporary directory to store the bundle
    with tempfile.TemporaryDirectory() as temp_dir:
        logging.debug(f"Copying bundle files to {temp_dir}")
        for filename in os.listdir(source_dir):
            subprocess.run(['cp', os.path.join(source_dir, filename), temp_dir], check=True)
        if external_rbac:
            logging.info(f"Copying external RBAC file {external_rbac} to {temp_dir}. Will need to update the bundle.yaml.")
            subprocess.run(['cp', external_rbac, temp_dir], check=True)
            _update_bundle(temp_dir)
        # zip and post the YAML to the URL
        with zipfile.ZipFile('bundle.zip', 'w') as zip_ref:
            for filename in os.listdir(temp_dir):
                zip_ref.write(os.path.join(temp_dir, filename), filename)
        with open('bundle.zip', 'rb') as f:
            # post as binary file
            response = requests.post(url, headers=headers, data=f)
    response.raise_for_status()
    # delete the zip file
    os.remove('bundle.zip')
    # print the response as pretty JSON
    try:
        response_json = response.json()
    except json.decoder.JSONDecodeError:
        die(f'Failed to decode JSON from response: {response.text}')
    click.echo(json.dumps(response_json, indent=2))
    # Filter out non-info messages
    if "validation-messages" not in response_json:
        logging.warning('No validation messages found in response. Is this an old CI version?')
        # check if the valid key exists and is True
        if "valid" not in response_json or not response_json["valid"]:
            die('Validation failed. See response for details.')
    else:
        non_info_messages = [message for message in response_json["validation-messages"] if not message.startswith("INFO -")]
        if non_info_messages:
            # if non info messages only include warnings...
            if all("WARNING -" in message for message in non_info_messages):
                if not ignore_warnings:
                    die('Validation failed with warnings')
                else:
                    logging.warning('Validation failed with warnings. Ignoring due to --ignore-warnings flag')
            else:
                die('Validation failed with errors or critical messages')

@click.pass_context
def update_plugins_options_null_check(ctx, plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, cap):
    cap = null_check(cap, 'cap', BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE, False, '')
    # fail fast if any strategy is passed explicitly
    default_plugins_json_list_strategy = PluginJsonListStrategy.AUTO.name
    default_plugins_json_merge_strategy = PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED.name
    default_catalog_warnings_strategy = CatalogWarningsStrategy.FAIL.name
    plugins_json_list_strategy = null_check(plugins_json_list_strategy, 'plugins_json_list_strategy', BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY, True, default_plugins_json_list_strategy)
    plugins_json_merge_strategy = null_check(plugins_json_merge_strategy, 'plugins_json_merge_strategy', BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY, True, default_plugins_json_merge_strategy)
    catalog_warnings_strategy = null_check(catalog_warnings_strategy, 'catalog_warnings_strategy', BUNDLEUTILS_CATALOG_WARNINGS_STRATEGY, True, default_catalog_warnings_strategy)
    logging.debug(f'Converting strategies to enums...')
    try:
        ctx.obj['plugins_json_list_strategy'] = PluginJsonListStrategy[plugins_json_list_strategy]
        ctx.obj['plugins_json_merge_strategy'] = PluginJsonMergeStrategy[plugins_json_merge_strategy]
        ctx.obj['catalog_warnings_strategy'] = CatalogWarningsStrategy[catalog_warnings_strategy]
    except KeyError:
        die(f'''Invalid strategy either:
            {plugins_json_list_strategy} (out of {get_name_from_enum(PluginJsonListStrategy)})
            or {plugins_json_merge_strategy} (out of {get_name_from_enum(PluginJsonMergeStrategy)})
            or {catalog_warnings_strategy} (out of {get_name_from_enum(CatalogWarningsStrategy)})
            ''')

@click.pass_context
def fetch_options_null_check(ctx, url, path, username, password, target_dir, keys_to_scalars, plugin_json_path, offline):
    # creds boolean True if URL set and not empty
    creds_needed = url is not None and url != ''
    offline = null_check(offline, 'offline', BUNDLEUTILS_FETCH_OFFLINE, False, '')
    url = lookup_url(url, '', False)
    username = null_check(username, USERNAME_ARG, BUNDLEUTILS_USERNAME, creds_needed)
    password = null_check(password, PASSWORD_ARG, BUNDLEUTILS_PASSWORD, creds_needed)
    path = null_check(path, PATH_ARG, BUNDLEUTILS_PATH, False)
    plugin_json_path = null_check(plugin_json_path, PLUGIN_JSON_PATH_ARG, BUNDLEUTILS_PLUGINS_JSON_PATH, False)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_FETCH_TARGET_DIR, False, default_target)
    keys_to_scalars = keys_to_scalars.split(',') if keys_to_scalars else []
    logging.debug(f'Using keys_to_scalars={keys_to_scalars}')
    keys_to_scalars = null_check(keys_to_scalars, KEYS_TO_CONVERT_TO_SCALARS_ARG, BUNDLEUTILS_KEYS_TO_CONVERT_TO_SCALARS, True, default_keys_to_scalars)
    # if path or url is not provided, look for a zip file in the current directory matching the pattern core-casc-export-*.zip
    if not path and not url:
        zip_files = glob.glob('core-casc-export-*.zip')
        if len(zip_files) == 1:
            logging.info(f'Found core-casc-export-*.zip file: {zip_files[0]}')
            path = zip_files[0]
        elif len(zip_files) > 1:
            die('Multiple core-casc-export-*.zip files found in the current directory')
    if not plugin_json_path and not url:
        plugin_json_files = glob.glob('plugins*.json')
        if len(plugin_json_files) == 1:
            logging.info(f'Found plugins*.json file: {plugin_json_files[0]}')
            plugin_json_path = plugin_json_files[0]
        elif len(plugin_json_files) > 1:
            die('Multiple plugins*.json files found in the current directory')

@bundleutils.command()
@update_plugins_options
@fetch_options
@click.pass_context
def fetch(ctx, url, path, username, password, target_dir, keys_to_scalars, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, offline, cap):
    """Fetch YAML documents from a URL or path."""
    set_logging(ctx)
    update_plugins_options_null_check(plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, cap)
    fetch_options_null_check(url, path, username, password, target_dir, keys_to_scalars, plugin_json_path, offline)
    try:
        fetch_yaml_docs()
    except Exception as e:
        die(f'Failed to fetch and write YAML documents: {e}')
    try:
        _update_plugins()
    except Exception as e:
        logging.error(f'Failed to fetch and update plugin data: {e}')
        raise e
    # TODO remove as soon as the export does not add '^' to variables
    handle_unwanted_escape_characters()

@click.pass_context
def handle_unwanted_escape_characters(ctx):
    target_dir = ctx.obj.get('target_dir')
    prefix = 'ESCAPE CHAR CHECK - SECO-3944: '
    # check in the jenkins.yaml file for the key 'cascItemsConfiguration.variableInterpolationEnabledForAdmin'
    jenkins_yaml = os.path.join(target_dir, 'jenkins.yaml')
    if not os.path.exists(jenkins_yaml):
        die(f"Jenkins YAML file '{jenkins_yaml}' does not exist (something seriously wrong here)")
    with open(jenkins_yaml, 'r') as f:
        jenkins_data = yaml.load(f)
    if 'unclassified' in jenkins_data and 'cascItemsConfiguration' in jenkins_data['unclassified'] and 'variableInterpolationEnabledForAdmin' in jenkins_data['unclassified']['cascItemsConfiguration']:
        pattern = r"\^{1,}\$\{"
        search_replace = '${'
        interpolation_enabled = jenkins_data['unclassified']['cascItemsConfiguration']['variableInterpolationEnabledForAdmin']
        if interpolation_enabled == 'true':
            # replace all instances of multiple '^' followed by with '${' with '^${' in the jenkins.yaml file
            pattern = r"\^{2,}\$\{"
            search_replace = '^${'
        items_yaml = os.path.join(target_dir, 'items.yaml')
        if os.path.exists(items_yaml):
            with open(items_yaml, 'r') as f:
                items_data = yaml.load(f)
            logging.info(f"{prefix}Variable interpolation enabled for admin = {interpolation_enabled}. Replacing '{pattern}' with '{search_replace}' in items.yaml")
            items_data = replace_string_in_dict(items_data, pattern, search_replace, prefix)
            logging.info(f"EQUAL DISPLAY_NAME CHECK: Setting 'displayName' to empty string if necessary...")
            items_data = replace_display_name_if_necessary(items_data)
        with open(items_yaml, 'w') as f:
                yaml.dump(items_data, f)

def replace_display_name_if_necessary(data):
    if isinstance(data, dict):
        # if dict has key 'displayName' and 'name' and they are the same, remove the 'displayName' key
        if 'displayName' in data and 'name' in data and data['displayName'] == data['name']:
            logging.debug(f"EQUAL DISPLAY_NAME CHECK: Setting 'displayName' to empty string since equal to name: {data['name']}")
            data['displayName'] = ''
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

def replace_string_in_dict(data, pattern, replacement, prefix=''):
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
                    if is_truthy(os.environ.get('BUNDLEUTILS_TRACE', '')):
                        logging.debug(f"{prefix}Replacing '{pattern}' with '{replacement}' in dict '{value}'")
                    else:
                        logging.debug(f"{prefix}Replacing '{pattern}' with '{replacement}' in dict (export BUNDLEUTILS_TRACE=1 for details)")
                    data[key] = re.sub(pattern, replacement, value)
    return data

def replace_string_in_list(data, pattern, replacement, prefix=''):
    for i, value in enumerate(data):
        if isinstance(value, dict):
            data[i] = replace_string_in_dict(value, pattern, replacement, prefix)
        elif isinstance(value, list):
            data[i] = replace_string_in_list(value, pattern, replacement, prefix)
        elif isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                logging.debug(f"{prefix}Replacing '{pattern}' with '{replacement}' in list '{value}'")
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
            logging.info(f"{plugin:40} < {str:40}")
        elif plugin not in col1:
            logging.info(f"{str:40} > {plugin:40}")
        else:
            logging.info(f"{plugin:40} | {plugin:40}")

def hline(text):
    logging.info("-" * 80)
    logging.info(text)
    logging.info("-" * 80)

# graph types
graph_type_all = 'all'
graph_type_minus_bootstrap = 'minus-bootstrap'
graph_type_minus_deleted_disabled = 'minus-deleted-disabled'

@click.pass_context
def _analyze_server_plugins(ctx, plugins_from_json, plugins_json_list_strategy, cap, url):
    logging.info("Plugin Analysis - Analyzing server plugins...")
    # Setup the dependency graphs
    graphs = {}
    graph_types = [graph_type_all, graph_type_minus_bootstrap, graph_type_minus_deleted_disabled]
    for graph_type in graph_types:
        graphs[graph_type] = {}
        dependency_graph = defaultdict(lambda: {"non_optional": [], "optional": [], "entry": {}})
        reverse_dependencies = defaultdict(list)
        graphs[graph_type]["dependency_graph"] = dependency_graph
        graphs[graph_type]["reverse_dependencies"] = reverse_dependencies
        # Build the dependency graph from the json data
        for plugin in plugins_from_json:
            if (graph_type in [graph_type_minus_bootstrap, graph_type_minus_deleted_disabled]) and plugin.get("bundled", True):
                continue
            if graph_type == graph_type_minus_deleted_disabled and (not plugin.get("enabled", True) or plugin.get("deleted", True)):
                continue
            plugin_name = plugin.get("shortName")
            dependency_graph[plugin_name]["entry"] = plugin
            plugin_dependencies = plugin.get("dependencies", [])
            for dependency in plugin_dependencies:
                dep_name = dependency.get("shortName")
                if dependency.get("optional", False):
                    dependency_graph[plugin_name]["optional"].append(dep_name)
                else:
                    dependency_graph[plugin_name]["non_optional"].append(dep_name)
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
            non_optional_deps.update(get_non_optional_dependencies(graph_type, dep, visited))
        return non_optional_deps

    # Function to find root plugins (those NOT listed as dependencies of any other plugin)
    def find_root_plugins(graph_type):
        dependency_graph = graphs[graph_type]["dependency_graph"]
        reverse_dependencies = graphs[graph_type]["reverse_dependencies"]
        all_plugins = set(dependency_graph.keys())
        all_dependencies = set(reverse_dependencies.keys())
        root_plugins = all_plugins - all_dependencies  # Plugins that are not dependencies
        return root_plugins

    # Function to recursively build a dependency tree as a list
    def build_dependency_list(graph_type, plugin_name, parent_line=None, output_list=None):
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
            logging.debug(f"Dependency tree for root plugin: {plugin}")
            dependency_list = build_dependency_list(graph_type, plugin)
            for line in render_dependency_list(dependency_list):
                logging.debug(line)
    for graph_type in graph_types:
        # create a list of all roots and their non-optional dependencies
        result = set()
        for plugin in graphs[graph_type]["roots"]:
            result.add(plugin)
            result.update(get_non_optional_dependencies(graph_type_all, plugin))
        graphs[graph_type]["roots-and-deps"] = result
    dgmbr = graphs[graph_type_minus_bootstrap]["roots"]
    dgmdr = graphs[graph_type_minus_deleted_disabled]["roots"]

    show_diff("Expected root plugins < vs > expected root plugins after deleted/disabled removed (any new roots on the right side are candidates for removal)", dgall.keys(), dgmbr, dgmdr)

    # handle the list strategy
    if plugins_json_list_strategy == PluginJsonListStrategy.ROOTS:
        expected_plugins = graphs[graph_type_minus_deleted_disabled]["roots"]
    elif plugins_json_list_strategy == PluginJsonListStrategy.ROOTS_AND_DEPS:
        expected_plugins = graphs[graph_type_minus_deleted_disabled]["roots-and-deps"]
    elif plugins_json_list_strategy == PluginJsonListStrategy.ALL:
        expected_plugins = list(dgall.keys())
    else:
        die(f"Invalid plugins json list strategy: {plugins_json_list_strategy.name}. Expected one of: {PluginJsonListStrategy.ALL.name}, {PluginJsonListStrategy.ROOTS.name}, {PluginJsonListStrategy.ROOTS_AND_DEPS.name}")

    # handle the removal of CAP plugin dependencies removal
    if cap:
        if plugins_json_list_strategy == PluginJsonListStrategy.ALL:
            logging.info(f"{BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE} option detected with ALL strategy. Ignoring...")
        else:
            logging.info(f"{BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE} option detected. Removing CAP plugin dependencies...")
            expected_plugins_copy = expected_plugins.copy()
            url, ci_version = lookup_url_and_version(url, '')
            if not url:
                die("No URL provided for CAP plugin removal")
            ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, '', '')
            jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
            envelope_json = jenkins_manager.get_envelope_json_from_war()
            envelope_json = json.loads(envelope_json)
            for plugin_id, plugin_info in envelope_json['plugins'].items():
                if plugin_info.get('scope') != 'bootstrap':
                    for dep in get_non_optional_dependencies(graph_type_all, plugin_id):
                        if dep in expected_plugins:
                            logging.debug(f"Removing dependency of {plugin_id}: {dep}")
                            expected_plugins.remove(dep)
            show_diff("Expected root plugins < vs > expected root plugins after CAP dependencies removed", dgall.keys(), expected_plugins_copy, expected_plugins)

    logging.info("Plugin Analysis - finished analysis.")

    # Sanity check:
    # reduced_plugins (and all non_optional_dependencies) + all_bootstrap_plugins (and all non_optional_dependencies) should be equal to original_plugins
    logging.debug("Plugin Analysis - Performing sanity check...")
    logging.debug("Plugin Analysis - Expecting expected_plugins + bootstrap_plugins + deleted_plugins (+ their non_optional_dependencies) should be equal to original_plugins")
    all_bootstrap_plugins = graphs[graph_type_all]["dependency_graph"].keys() - graphs[graph_type_minus_bootstrap]["dependency_graph"].keys()
    all_deleted_or_inactive_plugins = graphs[graph_type_all]["dependency_graph"].keys() - graphs[graph_type_minus_deleted_disabled]["dependency_graph"].keys()
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
        logging.error("Sanity check failed. Reduced plugins and bootstrap plugins do not match original plugins.")
        die("Sanity check failed. Reduced plugins and bootstrap plugins do not match original plugins.")
    else:
        logging.debug("Plugin Analysis - Sanity check passed.")

    expected_plugins = sorted(expected_plugins)
    return expected_plugins, all_bootstrap_plugins, all_deleted_or_inactive_plugins, graphs

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
        to_visit.update(reverse_dependency_graph[current])  # Add plugins that depend on `current`

    result.discard(target_plugin)  # Exclude the target plugin itself from the result
    return result

def find_plugin_by_id(plugins, plugin_id):
    logging.debug(f"Finding plugin by id: {plugin_id}")
    for plugin in plugins:
        if plugin.get('id') == plugin_id:
            return plugin
    return None

@bundleutils.command()
@update_plugins_options
@fetch_options
@click.pass_context
def update_plugins(ctx, url, path, username, password, target_dir, keys_to_convert, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, offline, cap):
    """Update plugins in the target directory."""
    set_logging(ctx)
    update_plugins_options_null_check(ctx, plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, cap)
    fetch_options_null_check(url, path, username, password, target_dir, keys_to_convert, plugin_json_path, offline)
    _update_plugins()


@bundleutils.command()
@update_plugins_options
@server_options
@click.option('-t', '--target-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory in which to update the plugins.yaml.')
@click.pass_context
def update_plugins_from_test_server(ctx, ci_type, ci_version, ci_server_home, target_dir, plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, cap):
    """
    Update plugins in the target directory using the plugins from the test server started for validation.
    """
    set_logging(ctx)
    update_plugins_options_null_check(plugins_json_list_strategy, plugins_json_merge_strategy, catalog_warnings_strategy, cap)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_type, ci_version, ci_server_home)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_MERGE_TRANSFORM_TARGET_DIR)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    ctx.obj['url'] = server_url
    ctx.obj['username'] = username
    ctx.obj['password'] = password
    _update_plugins()

@click.pass_context
def _update_plugins(ctx):
    username = ctx.obj.get('username')
    password = ctx.obj.get('password')
    target_dir = ctx.obj.get('target_dir')
    url = ctx.obj.get('url')
    plugin_json_path = ctx.obj.get('plugin_json_path')
    plugins_json_list_strategy = ctx.obj.get('plugins_json_list_strategy')
    plugins_json_merge_strategy = ctx.obj.get('plugins_json_merge_strategy')
    offline = ctx.obj.get('offline')
    cap = ctx.obj.get('cap')

    target_dir_offline = target_dir + '-offline'
    # handle offline mode
    if offline:
        if plugin_json_path:
            die('Offline mode is not supported with the path option')
        os.makedirs(target_dir_offline, exist_ok=True)
        export_json = os.path.join(target_dir_offline, 'export.json')
        if os.path.exists(export_json):
            logging.info(f'[offline] Offline export plugins.json file exists. Skipping fetch and using it instead.')
            plugin_json_path = export_json
            plugin_json_url = None
    else:
        remove_files_from_dir(target_dir_offline)

    # if no plugins_json_list_strategy is provided, determine it based on the apiVersion in the bundle.yaml file
    if plugins_json_list_strategy == PluginJsonListStrategy.AUTO:
        # find the apiVersion from the bundle.yaml file
        bundle_yaml = os.path.join(target_dir, 'bundle.yaml')
        if os.path.exists(bundle_yaml):
            with open(bundle_yaml, 'r') as f:
                bundle_yaml = yaml.load(f)
                api_version = bundle_yaml.get('apiVersion', '')
                if not api_version:
                    die('No apiVersion found in bundle.yaml file')
                # if either integer or string, convert to string
                if isinstance(api_version, int):
                    api_version = str(api_version)
                if api_version == '1':
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS_AND_DEPS
                    ctx.obj['plugins_json_list_strategy'] = plugins_json_list_strategy
                elif api_version == '2':
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS
                    ctx.obj['plugins_json_list_strategy'] = plugins_json_list_strategy
                else:
                    die(f"Invalid apiVersion found in bundle.yaml file: {api_version}")

    logging.info(f'Plugins JSON list strategy: {plugins_json_list_strategy.name} from {get_name_from_enum(PluginJsonListStrategy)}')
    logging.info(f'Plugins JSON merge strategy: {plugins_json_merge_strategy.name} from {get_name_from_enum(PluginJsonMergeStrategy)}')

    # load the plugin JSON from the URL or path
    plugin_json_str = None
    if plugin_json_path:
        logging.debug(f'Loading plugin JSON from path: {plugin_json_path}')
        with open(plugin_json_path, 'r') as f:
            plugin_json_str = f.read()
    elif url:
        plugin_json_url = url + plugin_json_url_path
        logging.debug(f'Loading plugin JSON from URL: {plugin_json_url}')
        plugin_json_str = call_jenkins_api(plugin_json_url, username, password)
        if offline:
            with open(export_json, 'w') as f:
                logging.info(f'[offline] Writing plugins.json to {export_json}')
                f.write(plugin_json_str)
    else:
        logging.info('No plugin JSON URL or path provided. Cannot determine if disabled/deleted plugins present in list.')
        return
    data = json.loads(plugin_json_str)
    plugins_from_json = data.get("plugins", [])
    expected_plugins, all_bootstrap_plugins, all_deleted_or_inactive_plugins, graphs = _analyze_server_plugins(plugins_from_json, plugins_json_list_strategy, cap, url)

    # checking the plugin-catalog.yaml file
    plugin_catalog_plugin_ids_previous = []
    plugin_catalog_plugin_ids = []
    plugin_catalog = os.path.join(target_dir, 'plugin-catalog.yaml')
    if os.path.exists(plugin_catalog):
        with open(plugin_catalog, 'r') as f:
            catalog_data = yaml.load(f)  # Load the existing data
        logging.info(f"Looking for disabled/deleted plugins to remove from plugin-catalog.yaml")
        # Check and remove plugins listed in filtered_plugins from includePlugins
        for configuration in catalog_data.get('configurations', []):
            if 'includePlugins' in configuration:
                for plugin_id in list(configuration['includePlugins']):
                    plugin_catalog_plugin_ids_previous.append(plugin_id)
                    if plugin_id in all_deleted_or_inactive_plugins:
                        if plugins_json_merge_strategy.should_delete:
                            logging.info(f" -> removing disabled/deleted plugin {plugin_id} according to merge strategy: {plugins_json_merge_strategy.name}")
                            del configuration['includePlugins'][plugin_id]
                        else:
                            logging.warning(f" -> unexpected plugin {plugin_id} found but not removed according to merge strategy: {plugins_json_merge_strategy.name}")
                            plugin_catalog_plugin_ids.append(plugin_id)
                    else:
                        plugin_catalog_plugin_ids.append(plugin_id)

        if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
            logging.info(f"Skipping writing to plugin-catalog.yaml according to merge strategy: {plugins_json_merge_strategy.name}")
        else:
            with open(plugin_catalog, 'w') as file:
                yaml.dump(catalog_data, file) # Write the updated data back to the file

    # removing from the plugins.yaml file
    plugins_file = os.path.join(target_dir, 'plugins.yaml')
    if os.path.exists(plugins_file):
        with open(plugins_file, 'r') as f:
            plugins_data = yaml.load(f)  # Load the existing data

        original_plugin_data = plugins_data.copy()
        current_plugins = []
        updated_plugins = []
        # Check if 'plugins' key exists and it's a list
        if 'plugins' in plugins_data and isinstance(plugins_data['plugins'], list):
            logging.debug(f"Found 'plugins' key in current plugins.yaml")
            current_plugins = plugins_data['plugins']

        logging.info(f"Looking for disabled/deleted plugins to remove from current plugins.yaml")
        for plugin in current_plugins:
            if plugin['id'] in plugin_catalog_plugin_ids:
                logging.info(f" -> skipping plugin {plugin['id']} due to entry in plugin-catalog.yaml")
                updated_plugins.append(plugin)
                continue
            if plugin['id'] in all_bootstrap_plugins:
                if plugins_json_merge_strategy == PluginJsonMergeStrategy.ALL:
                    logging.info(f" -> keeping bootstrap plugin {plugin['id']} according to merge strategy: {plugins_json_merge_strategy.name}")
                    updated_plugins.append(plugin)
                else:
                    logging.info(f" -> removing bootstrap plugin {plugin['id']}")
                continue
            if not plugin['id'] in expected_plugins:
                if plugins_json_merge_strategy.skip_pinned:
                    # if plugin map has a url or version, skip it
                    if 'url' in plugin:
                        logging.info(f" -> skipping plugin {plugin['id']} with pinned url according to merge strategy: {plugins_json_merge_strategy.name}")
                        updated_plugins.append(plugin)
                    elif 'version' in plugin:
                        logging.info(f" -> skipping plugin {plugin['id']} with pinned version according to merge strategy: {plugins_json_merge_strategy.name}")
                        updated_plugins.append(plugin)
                    else:
                        # find the plugins in the reverse_dependencies that are also in the expected_plugins
                        associated_parents = plugins_with_plugin_in_tree(graphs, graph_type_minus_bootstrap, plugin['id'])
                        expected_parents = ', '.join(associated_parents.intersection(expected_plugins))
                        logging.info(f" -> removing non-pinned plugin {plugin['id']} (parents: {expected_parents}) according to merge strategy: {plugins_json_merge_strategy.name}")
                elif plugins_json_merge_strategy.should_delete:
                    # find the plugins in the reverse_dependencies that are also in the expected_plugins
                    associated_parents = plugins_with_plugin_in_tree(graphs, graph_type_minus_bootstrap, plugin['id'])
                    expected_parents = ', '.join(associated_parents.intersection(expected_plugins))
                    logging.info(f" -> removing plugin {plugin['id']} (parents: {expected_parents}) according to merge strategy: {plugins_json_merge_strategy.name}")
                else:
                    logging.warning(f" -> plugin {plugin['id']} found but not removed according to merge strategy: {plugins_json_merge_strategy.name}")
                    updated_plugins.append(plugin)
            else:
                updated_plugins.append(plugin)

        # check for plugins that are installed and necessary but not in the plugins.yaml file
        # if the plugin is not in the plugins.yaml file, add it
        logging.info(f"Looking for plugins that are installed but not in the current plugins.yaml")
        for plugin in expected_plugins:
            found_plugin = find_plugin_by_id(current_plugins, plugin)
            if found_plugin is None:
                if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
                    logging.warning(f" -> found plugin installed on server but not present in bundle (skipping according to merge strategy: {plugins_json_merge_strategy.name}) : {plugin}")
                else:
                    logging.info(f" -> adding plugin expected but not present (according to strategy: {plugins_json_merge_strategy.name}) : {plugin}")
                    updated_plugins.append({'id': plugin})

        updated_plugins = sorted(updated_plugins, key=lambda x: x['id'])

        updated_plugins_ids = [plugin['id'] for plugin in updated_plugins]
        all_plugin_ids = set(updated_plugins_ids + expected_plugins)
        show_diff("Final merged plugins < vs > expected plugins after merging", all_plugin_ids, updated_plugins_ids, expected_plugins)
        if plugin_catalog_plugin_ids_previous:
            show_diff("Final merged catalog < vs > previous catalog after merging", plugin_catalog_plugin_ids + plugin_catalog_plugin_ids_previous, plugin_catalog_plugin_ids, plugin_catalog_plugin_ids_previous)

        plugins_data['plugins'] = updated_plugins
        if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
            logging.info(f"Skipping writing to plugins.yaml according to merge strategy: {plugins_json_merge_strategy.name}")
        else:
            if original_plugin_data != plugins_data:
                with open(plugins_file, 'w') as f:
                    logging.info(f"Writing updated plugins to {plugins_file}")
                    yaml.dump(plugins_data, f)  # Write the updated data back to the file
            else:
                logging.info(f"No changes detected in {plugins_file}. Skipping write.")

def remove_files_from_dir(dir):
    if os.path.exists(dir):
        logging.debug(f'Removing files from directory: {dir}')
        for filename in os.listdir(dir):
            filename = os.path.join(dir, filename)
            os.remove(filename)

@click.pass_context
def fetch_yaml_docs(ctx):
    url = ctx.obj.get('url')
    path = ctx.obj.get('path')
    username = ctx.obj.get('username')
    password = ctx.obj.get('password')
    target_dir = ctx.obj.get('target_dir')
    offline = ctx.obj.get('offline')
    # place each document in a separate file under a target directory
    logging.debug(f'Creating target directory: {target_dir}')
    os.makedirs(target_dir, exist_ok=True)

    # handle offline mode
    target_dir_offline = target_dir + '-offline'
    if offline:
        if path:
            die('Offline mode is not supported with the path option')
        os.makedirs(target_dir_offline, exist_ok=True)
        export_yaml = os.path.join(target_dir_offline, 'export.yaml')
        if os.path.exists(export_yaml):
            logging.info(f'Offline export YAML file exists. Skipping fetch and using it instead.')
            path = export_yaml
            url = None
    else:
        remove_files_from_dir(target_dir_offline)

    # remove any existing files
    remove_files_from_dir(target_dir)

    if path:
        # if the path points to a zip file, extract the YAML from the zip file
        if path.endswith('.zip'):
            logging.info(f'Extracting YAML from ZIP file: {path}')
            with zipfile.ZipFile(path, 'r') as zip_ref:
                # list the files in the zip file
                for filename in zip_ref.namelist():
                    # read the YAML from the file
                    with zip_ref.open(filename) as f:
                        # if file is empty, skip
                        if f.read(1):
                            f.seek(0)
                            response_text = f.read()
                            response_text = preprocess_yaml_text(response_text)
                            logging.debug(f'Read YAML from file: {filename}')
                            doc = yaml.load(response_text)
                            write_yaml_doc(doc, target_dir, filename)
                        else:
                            logging.warning(f'Skipping empty file: {filename}')
        else:
            logging.info(f'Read YAML from path: {path}')
            with open(path, 'r') as f:
                response_text = f.read()
                response_text = preprocess_yaml_text(response_text)
                yaml_docs = list(yaml.load_all(response_text))
                write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    elif url:
        if fetch_url_path not in url:
            url = url + fetch_url_path
        logging.info(f'Read YAML from url: {url}')
        response_text = call_jenkins_api(url, username, password)
        if offline:
            with open(export_yaml, 'w') as f:
                f.write(response_text)
        response_text = preprocess_yaml_text(response_text)
        # logging.debug(f'Fetched YAML from url {url}:\n{response_text}')
        yaml_docs = list(yaml.load_all(response_text))
        write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    else:
        die('No path or URL provided')

@click.pass_context
def preprocess_yaml_text(ctx, response_text):
        catalog_warnings_strategy = ctx.obj.get('catalog_warnings_strategy')
        if isinstance(response_text, bytes):
            response_text = response_text.decode('utf-8')
        # find any occurrences of "^--- .*$"
        matching_lines = re.findall(r'^--- .*$', response_text, re.MULTILINE)
        if matching_lines:
            # log results
            for line in matching_lines:
                logging.warning(f'Found catalog warnings: {line}')
            if catalog_warnings_strategy == CatalogWarningsStrategy.COMMENT:
                logging.warning(f'Found catalog warnings in the response. Converting to comments according to strategy {catalog_warnings_strategy.name}')
                response_text = re.sub(r'^--- .*$',r'# \g<0>', response_text, flags=re.MULTILINE)
            elif catalog_warnings_strategy == CatalogWarningsStrategy.FAIL:
                die(f'''
                    Found catalog warnings in the response. Exiting according to strategy {catalog_warnings_strategy.name}
                    Either fix the warnings or change the strategy to {CatalogWarningsStrategy.COMMENT.name} to convert warnings to comments.''')
            else:
                die(f'Invalid catalog warnings strategy: {catalog_warnings_strategy.name}. Expected one of: {get_name_from_enum(CatalogWarningsStrategy)}')
        return response_text

def call_jenkins_api(url, username, password):
    logging.debug(f'Fetching response from URL: {url}')
    logging.debug(f'Using username: {username}')
    # print last 5 characters of password
    logging.debug(f'Using password: ...{password[-5:]}')
    headers = {}
    if username and password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
    response = requests.get(url, headers=headers)
    response.raise_for_status()
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
    filename = os.path.join(target_dir, filename)
    doc = preprocess_yaml_object(doc)

    # create a new file for each YAML document
    with open(filename, 'w') as f:
        # dump without quotes for strings and without line break at the end
        yaml.dump(doc, f)
        logging.info(f'Wrote {filename}')
    # remove the last empty line break if necessary
    with open(filename, 'r') as f:
        lines = f.readlines()
    if lines and lines[-1] == '\n':
        lines = lines[:-1]
    with open(filename, 'w') as f:
        f.writelines(lines)

def traverse_credentials(hash_only, hash_seed, filename, obj, custom_replacements={}, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else f"/{k}"
            # does custom_replacements contain an id that matches the id in the object and a key matching k?
            if isinstance(v, str) and 'id' in obj:
                id = obj['id']
                matching_tuple = None
                # hashing only for auditing purposes - no need to check for custom replacements
                if not hash_only:
                    custom_replacements_for_id = [item for item in custom_replacements if item['id'] == id]
                    for custom_replacement in custom_replacements_for_id:
                        if k in custom_replacement:
                            matching_tuple = custom_replacement
                if re.match(r'{.*}', v) or matching_tuple is not None:
                    if hash_only:
                        # create a hash of the hash_seed + v
                        replacement = hashlib.sha256((hash_seed + v).encode()).hexdigest()
                    elif matching_tuple is None or k not in matching_tuple:
                        logging.debug(f"Matching tuple NOT found. Creating replacement for {id} and {k}")
                        # create a string consisting of:
                        # - all non-alphanumeric characters changed to underscores
                        # - the id and k joined with an underscore
                        # - all uppercased
                        replacement = "${" + re.sub(r'\W', '_', id + "_" + k).upper() + "}"
                    else:
                        logging.debug(f"Matching tuple found: {matching_tuple}")
                        replacement = matching_tuple[k]

                    if replacement == BUNDLEUTILS_CREDENTIAL_DELETE_SIGN:
                        parent_path = re.sub(r'/[^/]*$', '', path)
                        logging.warning(f"Found a credential '{id}' string that needs to be deleted at path: {parent_path}")
                        # print the JSON Patch operation for the deletion of the parent object
                        patch = {"op": "remove", "path": f'{parent_path}'}
                        apply_patch(filename, [patch])
                        break
                    else:
                        # print the JSON Patch operation for the replacement
                        patch = {"op": "replace", "path": f'{new_path}', "value": f'{replacement}'}
                        apply_patch(filename, [patch])
                        continue
            traverse_credentials(hash_only, hash_seed, filename, v, custom_replacements, new_path)
    elif isinstance(obj, list):
        # traverse the list in reverse order to avoid index issues when deleting items
        for i, v in enumerate(reversed(obj)):
            # Calculate the original index by subtracting the reversed index from the length of the list minus 1
            original_index = len(obj) - 1 - i
            new_path = f"{path}/{original_index}"
            traverse_credentials(hash_only, hash_seed, filename, v, custom_replacements, new_path)
    else:
        if isinstance(obj, str) and re.match(r'{.*}', obj):
            # if the string is a replacement string, raise an exception
            logging.warning(f"Found a non-credential string (no id found) that needs to be replaced at path: {path}")
            if hash_only:
                # create a hash of the hash_seed + v
                replacement = hashlib.sha256((hash_seed + v).encode()).hexdigest()
            else:
                # the replacement string should be in the format ${ID_KEY}
                replacement = "${" + re.sub(r'\W', '_', path.removeprefix('/')).upper() + "}"
            # print the JSON Patch operation for the replacement
            patch = {"op": "replace", "path": f'{path}', "value": f'{replacement}'}
            apply_patch(filename, [patch])

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
            if isinstance(current, list) and isinstance(key, int) and key < len(current):
                recurse(current[key], parts_remaining[1:], path_so_far + [key])
            elif isinstance(current, dict) and key in current:
                recurse(current[key], parts_remaining[1:], path_so_far + [key])

    recurse(data, parts, [])
    return results

def expand_patch_paths(obj, patch_list):
    expanded = []

    for patch in patch_list:
        matches = resolve_paths_with_selectors(obj, patch['path'])  # use our earlier function
        for path_parts in matches:
            json_ptr = "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in path_parts)
            new_patch = patch.copy()
            new_patch["path"] = json_ptr
            expanded.append(new_patch)

    return expanded


def apply_patch(filename, patch_list):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)

    if obj is None:
        logging.error(f'Failed to load YAML object from file {filename}')
        return

    # Expand wildcard/selector paths before applying
    expanded_patches = expand_patch_paths(obj, patch_list)
    logging.debug(f"Expanded patches:\n{printYaml(expanded_patches)}")

    # for each patch, apply the patch to the object
    for patch in expanded_patches:
        # if not an add operation
        if patch['op'] != 'add':
            # Check if the path exists
            try:
                patch_path = patch['path']
                logging.debug(f'Checking if path exists for patch path: {patch_path}')
                jsonpointer.resolve_pointer(obj, patch_path)
            except jsonpointer.JsonPointerException:
                # If the path does not exist, skip the patch
                logging.debug(f'Ignoring non-existent path {patch["path"]} in {filename}')
                continue
        # Apply the patch
        patch = jsonpatch.JsonPatch([patch])
        try:
            logging.debug(f'Applying JSON patch to {filename}')
            logging.debug(f' ->' + str(patch))
            obj = patch.apply(obj)
        except jsonpatch.JsonPatchConflict:
            logging.error('Failed to apply JSON patch')
            return

    # save the patched object back to the file
    with open(filename, 'w') as out:
        yaml.dump(obj, out)

def handle_patches(patches, target_dir):
    # if patches is empty, skip
    if not patches:
        logging.info('Transform: no JSON patches to apply')
        return
    # for each key in the patches, open the file and apply the patch
    for filename, patch in patches.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            logging.info(f'File {filename} does not exist. Skipping patching.')
            continue
        logging.info(f'Transform: applying JSON patches to {filename}')
        apply_patch(filename, patch)

@click.pass_context
def apply_replacements(ctx, filename, custom_replacements):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)
        if obj is None:
            logging.error(f'Failed to load YAML object from file {filename}')
            return
        hash_only = is_truthy(os.environ.get(BUNDLEUTILS_CREDENTIAL_HASH, 'false'))
        hash_seed = ctx.obj.get('hash_seed', '')
        if hash_only:
            if hash_seed is None or hash_seed == '':
                logging.info(f'Hashing encrypted data without seed')
            else:
                logging.info(f'Hashing encrypted data with seed')
        traverse_credentials(hash_only, hash_seed, filename, obj, custom_replacements)

def handle_credentials(credentials, target_dir):
    # if credentials is empty, skip
    if not credentials:
        logging.info('Transform: no credentials to replace')
        return
    # for each key in the patches, open the file and apply the patch
    for filename, replacements in credentials.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            continue
        logging.info(f'Transform: applying cred replacements to {filename}')
        apply_replacements(filename, replacements)

def handle_substitutions(substitutions, target_dir):
    # if substitutions is empty, skip
    if not substitutions:
        logging.info('Transform: no substitutions to apply')
        return
    # for each key in the patches, open the file and apply the patch
    for filename, replacements in substitutions.items():
        filename = os.path.join(target_dir, filename)
        if not _file_check(filename):
            continue
        logging.info(f'Transform: applying substitutions to {filename}')
        with open(filename, 'r') as inp:
            # use pattern as a regex to replace the text in the file
            text = inp.read()
            for replacement in replacements:
                pattern = replacement['pattern']
                value = replacement['value']
                logging.debug(f'Applying substitution: {pattern} -> {value}')
                text = re.sub(pattern, value, text)
            with open(filename, 'w') as out:
                out.write(text)
            logging.info(f'Wrote {filename}')

def handle_splits(splits, target_dir):
    # if splits is empty, skip
    if not splits:
        logging.info('Transform: no splits to apply')
        return
    # for type in items, jcasc, if the key exists, process
    for split_type, split_dict in splits.items():
        if split_type == 'items':
            for filename, configs in split_dict.items():
                logging.info(f'Transform: applying item split to {target_dir}/{filename}')
                logging.debug(f'Using configs: {configs}')
                split_items(target_dir, filename, configs)
        elif split_type == 'jcasc':
            for filename, configs in split_dict.items():
                logging.info(f'Applying jcasc split to {target_dir}/{filename}')
                logging.debug(f'Using configs: {configs}')
                split_jcasc(target_dir, filename, configs)

def _convert_to_dict(obj):
    """ Recursively convert CommentedMap and CommentedSeq to dict and list."""
    if isinstance(obj, dict):
        return {k: _convert_to_dict(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_convert_to_dict(v) for v in obj]
    return obj

def printYaml(obj, convert=False):
    # needed to remove comments and '!!omap' identifiers
    obj2 = _convert_to_dict(obj) if convert else obj
    stream = io.StringIO()
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
    logging.debug(f'Obj1 ----> Key: {type(obj1)} Value: {obj1}')
    logging.debug(f'Obj2 ----> Key: {type(obj2)} Value: {obj2}')

    if isinstance(obj2, CommentedMap):
        for key, value in obj2.items():
            if key not in obj1 or obj1[key] is None:
                if isinstance(value, CommentedMap):
                    obj1[key] = {}
                elif isinstance(value, CommentedSeq):
                    obj1[key] = []
            recursive_merge(obj1[key], uncomment(value))
    elif isinstance(obj2, CommentedSeq):
        for value in obj2:
            if value not in obj1:
                obj1.append(uncomment(value))
    else:
        logging.debug(f'Unkown type: {type(obj2)}')
    return obj1

def source_target_prep(source_dir, target_dir, configs, suffix, filename):
    if not source_dir:
        source_dir = default_target
    source_dir = os.path.normpath(source_dir)
    if not target_dir:
        target_dir = source_dir + suffix
    target_dir = os.path.normpath(target_dir)
    if not configs:
        # if a normalize.yaml file is found in the current directory, use it
        if os.path.exists(filename):
            logging.info(f'Using {filename} in the current directory')
            configs = [filename]
        else:
            path = get_config_file(filename)
            configs = [path]
    return source_dir, target_dir, configs

@bundleutils.command()
@transform_options
@click.pass_context
def normalize(ctx, strict, configs, source_dir, target_dir, dry_run):
    """Transform using the normalize.yaml for better comparison."""
    set_logging(ctx)
    source_dir, target_dir, configs = source_target_prep(source_dir, target_dir, configs, '-normalized', 'normalize.yaml')
    _transform(configs, source_dir, target_dir, dry_run)

@bundleutils.command()
@transform_options
@click.option('-H', '--hash-seed', help=f"""
    Optional prefix for the hashing process (also {BUNDLEUTILS_CREDENTIAL_HASH_SEED}).

    NOTE: Ideally, this should be a secret value that is not shared with anyone. Changing this value will result in different hashes.""")
@click.pass_context
def audit(ctx, strict, configs, source_dir, target_dir, hash_seed, dry_run):
    """
    Transform using the normalize.yaml but obfuscating any sensitive data.

    NOTE: The credentials and sensitive data will be hashed and cannot be used in an actual bundle.
    """
    set_logging(ctx)

    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_AUDIT_SOURCE_DIR)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_AUDIT_TARGET_DIR)
    configs = null_check(configs, 'configs', BUNDLEUTILS_AUDIT_CONFIGS, False)

    os.environ[BUNDLEUTILS_CREDENTIAL_HASH] = 'true'
    null_check(hash_seed, 'hash_seed', BUNDLEUTILS_CREDENTIAL_HASH_SEED, False,'')

    source_dir, target_dir, configs = source_target_prep(source_dir, target_dir, configs, '-audit', 'normalize.yaml')
    _transform(configs, source_dir, target_dir, dry_run)

@bundleutils.command()
@transform_options
@click.pass_context
def transform(ctx, strict, configs, source_dir, target_dir, dry_run):
    """Transform using a custom transformation config."""
    set_logging(ctx)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_TRANSFORM_SOURCE_DIR)
    source_dir = os.path.normpath(source_dir)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_TRANSFORM_TARGET_DIR)
    target_dir = os.path.normpath(target_dir)
    configs = null_check(configs, 'configs', BUNDLEUTILS_TRANSFORM_CONFIGS, False)
    _transform(configs, source_dir, target_dir, dry_run)

@click.pass_context
def _file_check(ctx, file, strict=False):
    # if file does not exist, or is empty, skip
    logging.debug(f'Checking file: {file}')
    # resolve the file to a relative path
    file = os.path.abspath(file)
    if not os.path.exists(file) or os.path.getsize(file) == 0:
        # if default_fail_on_missing is set, raise an exception
        if ctx.params["strict"] or strict:
            die(f'File {file} does not exist')
        logging.warning(f'File {file} does not exist. Skipping.')
        return False
    return True

def _transform(configs, source_dir, target_dir, dry_run = False):
    """Transform using a custom transformation config."""
    # add the transformation configs recursively into the merged config
    # if the configs is a string, split it by space
    if isinstance(configs, str):
        configs = configs.split()
    if not configs:
        # if a transform.yaml file is found in the current directory, use it
        if os.path.exists('transform.yaml'):
            logging.info('Using transform.yaml in the current directory')
            configs = ['transform.yaml']
        else:
            die('No transformation config provided and no transform.yaml found in the current directory')
    merged_config = {}
    for config in configs:
        _file_check(config, True)
        with open(config, 'r') as inp:
            logging.info(f'Transformation: processing {config}')
            obj = yaml.load(inp)
            merged_config = recursive_merge(merged_config, obj)

    if dry_run:
        logging.info(f'Merged config:\n' + printYaml(merged_config))
        return

    logging.debug(f'Merged config:\n' + printYaml(merged_config))
    source_dir = os.path.normpath(source_dir)
    # if the target directory is not set, use the source directory suffixed with -transformed
    if not target_dir:
        target_dir = source_dir + '-transformed'
    target_dir = os.path.normpath(target_dir)
    logging.info(f'Transform: source {source_dir} to target {target_dir}')
    # create the target directory if it does not exist, delete all files in it
    os.makedirs(target_dir, exist_ok=True)
    for filename in os.listdir(target_dir):
        filename = os.path.join(target_dir, filename)
        os.remove(filename)
    # copy all files from the source directory to the target directory
    for filename in os.listdir(source_dir):
        source_filename = os.path.join(source_dir, filename)
        target_filename = os.path.join(target_dir, filename)
        logging.debug(f'Copying {source_filename} to {target_filename}')
        with open(source_filename, 'r') as inp:
            obj = yaml.load(inp)
        with open(target_filename, 'w') as out:
            yaml.dump(obj, out)

    handle_patches(merged_config.get('patches', {}), target_dir)
    handle_credentials(merged_config.get('credentials', []), target_dir)
    handle_substitutions(merged_config.get('substitutions', {}), target_dir)
    handle_splits(merged_config.get('splits', {}), target_dir)
    _update_bundle(target_dir)

@click.pass_context
def preprocess_yaml_object(ctx, data, parent_key = None):
    if isinstance(data, CommentedMap):
        # Remove empty keys
        keys_to_remove = [k for k in data if k == ""]
        if keys_to_remove:
            logging.debug(f"Removed empty keys from {type(data)}: {data}")
            for key in keys_to_remove:
                del data[key]
        # Convert values to block scalars if needed
        convert_to_scalars = [k for k in data if k in ctx.obj.get(KEYS_TO_CONVERT_TO_SCALARS_ARG)]
        for key in convert_to_scalars:
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
                    logging.warning(f"MISSING VALUE STRING - BEE-29822: Adding value = '' to entry for key: {item['key']}")
                    item['value'] = ""
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

@bundleutils.command()
@click.option('-t', '--target-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory to update the bundle.yaml file (defaults to CWD).')
@click.option('-d', '--description', help=f'Optional description for the bundle (also {BUNDLEUTILS_BUNDLE_DESCRIPTION}).')
@click.option('-o', '--output-sorted', help=f'Optional place to put the sorted yaml string used to created the version.')
@click.option('-e', '--empty-bundle-strategy', help=f'Optional strategy for handling empty bundles ({BUNDLEUTILS_EMPTY_BUNDLE_STRATEGY}).')
@click.pass_context
def update_bundle(ctx, target_dir, description, output_sorted, empty_bundle_strategy):
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
    set_logging(ctx)
    _update_bundle(target_dir, description, output_sorted, empty_bundle_strategy)

def _basename(dir):
    return os.path.basename(os.path.normpath(dir))

def _get_files_for_key(target_dir, key):
        files = []
        # Special case for 'jcasc'
        if key == 'jcasc':
            prefixes = ['jenkins', 'jcasc']
        elif key == 'catalog':
            prefixes = ['plugin-catalog']
        else:
            prefixes = [key]

        for prefix in prefixes:
            # Add list of YAML files matching .*prefix.* and ending with .yaml
            for file in os.listdir(target_dir):
                if re.match(rf'.*{prefix}.*\.yaml', file) and not file == f'{prefix}.yaml':
                    files.append(os.path.join(target_dir, file))
        files = sorted(files)

        for prefix in prefixes:
            # if exact match exists, add to front
            exact_match = os.path.join(target_dir, f'{prefix}.yaml')
            if os.path.exists(exact_match):
                logging.debug(f'Found exact match for {key}: {exact_match}')
                files.insert(0, exact_match)
                break

        # remove any empty files
        files = [file for file in files if _file_check(file)]
        for file in files:
            logging.debug(f'File for {key}: {file}')

        # special case for 'plugins'. If any of the files does not contain the yaml key 'plugins', remove the key from the data
        if key == 'jcasc':
            for file in files:
                with open(file, 'r') as f:
                    jcasc_file = yaml.load(f)
                    # if jenkins the only key and jenkins is empty, remove the file from the list
                    if jcasc_file.keys() == ['jenkins'] and not jcasc_file['jenkins']:
                        logging.info(f'Removing {file} from the list due to missing or empty jenkins')
                        files.remove(file)

        # special case for 'plugins'. If any of the files does not contain the yaml key 'plugins', remove the key from the data
        if key == 'plugins':
            for file in files:
                with open(file, 'r') as f:
                    plugins_file = yaml.load(f)
                    # if no plugins key or plugins is empty, remove the file from the list
                    if 'plugins' not in plugins_file or not plugins_file['plugins']:
                        logging.info(f'Removing {file} from the list due to missing or empty plugins')
                        files.remove(file)
                        os.remove(file)

        # special case for 'catalog'. If any of the files does not contain the yaml key 'configurations', remove the key from the data
        if key == 'catalog':
            for file in files:
                with open(file, 'r') as f:
                    catalog_file = yaml.load(f)
                    # if no configurations key or configurations is empty, remove the file from the list
                    if 'configurations' not in catalog_file or not catalog_file['configurations']:
                        logging.info(f'Removing {file} from the list due to missing or empty configurations')
                        files.remove(file)
                        os.remove(file)

        # special case for 'items'. If any of the files does not contain the yaml key 'items', remove the key from the data
        if key == 'items':
            for file in files:
                with open(file, 'r') as f:
                    items_file = yaml.load(f)
                    # if no items key or items is empty, remove the file from the list
                    if 'items' not in items_file or not items_file['items']:
                        logging.info(f'Removing {file} from the list due to missing or empty items')
                        files.remove(file)
                        os.remove(file)

        # special case for 'rbac'. If any of the files does not contain the yaml key 'roles' and 'groups', remove the key from the data
        if key == 'rbac':
            for file in files:
                with open(file, 'r') as f:
                    rbac_file = yaml.load(f)
                    # if no roles key or roles is empty, remove the file from the list
                    if ('roles' not in rbac_file or not rbac_file['roles']) and ('groups' not in rbac_file or not rbac_file['groups']):
                        logging.info(f'Removing {file} from the list due to missing or empty roles and groups')
                        files.remove(file)
                        os.remove(file)
        logging.info(f'Files for {key}: {files}')
        return files

@click.pass_context
def _update_bundle(ctx, target_dir, description=None, output_sorted=None, empty_bundle_strategy=None):
    description = null_check(description, 'description', BUNDLEUTILS_BUNDLE_DESCRIPTION, False)
    empty_bundle_strategy = null_check(empty_bundle_strategy, 'empty_bundle_strategy', BUNDLEUTILS_EMPTY_BUNDLE_STRATEGY, False, default_empty_bundle_strategy)

    if not target_dir:
        target_dir = ctx.obj.get(ORIGINAL_CWD)
    logging.info(f'Updating bundle in {target_dir}')
    # Load the YAML file
    with open(os.path.join(target_dir, 'bundle.yaml'), 'r') as file:
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
                logging.info(f'Removing key {key} from the bundle as no files were found')
                del data[key]
            continue

        # Update the key in the data
        logging.debug(f'Updated {key} to {files}')
        data[key] = files

        # Add the files to the all_files list
        all_files.extend(files)

    if len(all_files) == 0:
        if empty_bundle_strategy == 'delete':
            logging.warning(f'Empty Bundle Strategy: No files found. Removing target directory {target_dir}')
            shutil.rmtree(target_dir)
            return
        elif empty_bundle_strategy == 'fail':
            die(f'Empty Bundle Strategy: No files found for bundle.yaml {target_dir}/bundle.yaml')
        elif empty_bundle_strategy == 'noop':
            logging.info('Empty Bundle Strategy: No files found. Creating an empty jenkins.yaml')
            data['jcasc'] = 'jenkins.yaml'
            with open(os.path.join(target_dir, 'jenkins.yaml'), 'w') as file:
                yaml.dump({"jenkins": {}}, file)
        else:
            die(f"Empty Bundle Strategy: Strategy '{empty_bundle_strategy}' not supported. {BUNDLEUTILS_EMPTY_BUNDLE_STRATEGY} must be one of {empty_bundle_strategies}")

    # update the id key with the basename of the target_dir
    data['id'] = _basename(target_dir)
    data['description'] = f"Bundle for {data['id']}" if not description else description

    # update the version key with the md5sum of the content of all files
    data['version'] = generate_collection_uuid(target_dir, all_files, output_sorted)
    logging.info(f'Updated version to {data["version"]}')


    # Save the YAML file
    logging.info(f'Wrote {target_dir}/bundle.yaml')
    with open(os.path.join(target_dir, 'bundle.yaml'), 'w') as file:
        yaml.dump(data, file)

def get_nested(data, path):
    """Get a nested item from a dictionary."""
    keys = path.split('/')
    for key in keys:
        if key in data:
            data = data[key]
        else:
            return None
    return data

def set_nested(data, path, value):
    """Set a nested item in a dictionary."""
    keys = path.split('/')
    finaldest = data
    for key in keys[:-1]:
        data.setdefault(key, {})
        finaldest = data[key]
    finaldest[keys[-1]] = value

def del_nested(data, path):
    """Delete a nested item from a dictionary."""
    keys = path.split('/')
    for key in keys[:-1]:
        data = data[key]
    del data[keys[-1]]

def split_jcasc(target_dir, filename, configs):
    logging.info('Loading YAML object')

    full_filename = os.path.join(target_dir, filename)
    if not _file_check(full_filename):
        return
    with open(full_filename, 'r') as f:
        source_data = yaml.load(f)

    # For each target in the configuration...
    for config in configs:
        target = config['target']
        paths = config['paths']

        # NOTE on paths:
        # - the path may have an asterisk at the end and after the last slash
        # - this will to affect all keys under that path
        # - this can only happen in conjunction with the 'auto' or 'delete' target
        # - if either of these conditions are not met, it will error out
        new_paths = []
        for path in paths:
            if path.endswith('/*'):
                if target != 'auto' and target != 'delete':
                    die(f'Path {path} must use target "auto" or "delete"')
                logging.debug(f'Moving all keys under {path} to {target}')
                if path == '/*':
                    path = ''
                    data = source_data
                else:
                    path = path[:-2]
                    data = get_nested(source_data, path)
                if data is None:
                    logging.info(f'No data found at {path}')
                    continue
                for key in data.keys():
                    if path:
                        logging.debug(f' - > {path}/{key}')
                        new_paths.append(f'{path}/{key}')
                    else:
                        logging.debug(f' - > {key}')
                        new_paths.append(f'{key}')
            else:
                # delete leading slash if it exists
                if path.startswith('/'):
                    logging.debug(f'Removing leading slash from path: {path}')
                    path = path[1:]
                new_paths.append(path)

        logging.debug(f'Old paths before wildcards: {new_paths}')
        logging.debug(f'New paths after wildcards: {new_paths}')
        if is_truthy(os.environ.get('BUNDLEUTILS_TRACE', '')):
            logging.debug(f'Source data: \n{printYaml(source_data)}')

        # For each path to move...
        for path in new_paths:
            # Check if the path exists in the source file
            if get_nested(source_data, path) is not None:
                # Determine the target file name
                if target == 'auto':
                    target_file = path.replace('/', '.') + '.yaml'
                else:
                    target_file = target

                if target_file == 'delete':
                    logging.info(f'Deleting {path}')
                    del_nested(source_data, path)
                else:
                    target_file = os.path.join(target_dir, 'jenkins.' + target_file)
                    logging.debug(f'Moving {path} to {target_file}')

                    # Load the target file if it exists, or create a new one if it doesn't
                    if os.path.exists(target_file):
                        logging.debug(f'Loading existing target file {target_file}')
                        with open(target_file, 'r') as file:
                            target_data = yaml.load(file)
                    else:
                        logging.debug(f'Creating new target file {target_file}')
                        target_data = {}

                    # Move the path from the source file to the target file
                    set_nested(target_data, path, get_nested(source_data, path))
                    del_nested(source_data, path)

                    # Save the target file
                    if target_data:
                        logging.info(f'Saving target file {target_file}')
                        with open(target_file, 'w') as file:
                            yaml.dump(target_data, file)
                    else:
                        logging.info(f'No data found at {path}. Skipping saving target file {target_file}')
            else:
                logging.debug(f'Path {path} not found in source file')

    # Save the modified source file if it has any data left
    if source_data:
        logging.info(f'Saving source file {full_filename}')
        with open(full_filename, 'w') as file:
            yaml.dump(source_data, file)
        # rename the source files base name to "'jenkins.' + filename" if not already done
        if not filename.startswith('jenkins.'):
            new_filename = os.path.join(target_dir, 'jenkins.' + filename)
            logging.info(f'Renaming {full_filename} to {new_filename}')
            os.rename(full_filename, new_filename)
    else:
        logging.info(f'No data left in source file. Removing {full_filename}')
        os.remove(full_filename)

def split_items(target_dir, filename, configs):
    logging.debug(f'Loading YAML object from {filename}')

    full_filename = os.path.join(target_dir, filename)
    if not _file_check(full_filename):
        return
    with open(full_filename, 'r') as f:
        data = yaml.load(f)

    new_data = {}
    removed_items = []

    # if items exist in the source file...
    if 'items' not in data:
        logging.info(f'No items found in {full_filename}')
        items = []
    else:
        items = data['items']
    for config in configs:
        target = config['target']
        for item in items:
            if item in removed_items:
                continue
            item_name = item['name']
            logging.info(f'Checking item {item_name} (target: {target})')
            for pattern in config['patterns']:
                logging.info(f'Checking for pattern {pattern}')
                if re.match(pattern, item_name):
                    logging.info(f' - > matched {item_name}')
                    if target == 'auto':
                        target_file = item_name + '.yaml'
                    else:
                        target_file = target
                    removed_items.append(item)
                    if target_file == 'delete':
                        logging.info(f' - > ignoring {item_name} to {target_file}')
                    else:
                        if target_file not in new_data:
                            new_data[target_file] = []
                        new_data[target_file].append(item)
                        logging.info(f' - > moving {item_name} to {target_file}')

    # Remove the items that were moved
    for item in removed_items:
        items.remove(item)
    # if there are no items left, remove the file instead of dumping it
    if not items:
        logging.info(f'No items left in file. Removing {full_filename}')
        os.remove(full_filename)
    else:
        # Save the modified source file
        with open(full_filename, 'w') as f:
            yaml.dump(data, f)

    # rename the source files base name to "'items.' + filename" if not already done
    if not filename.startswith('items.'):
        new_filename = os.path.join(target_dir, 'items.' + filename)
        logging.info(f'Renaming {full_filename} to {new_filename}')
        os.rename(full_filename, new_filename)

    logging.info(f'Writing files to {target_dir}')
    for pattern_filename, items in new_data.items():
        new_file_path = os.path.join(target_dir, 'items.' + pattern_filename)
        logging.info(f'Writing {new_file_path}')
        with open(new_file_path, 'w') as f:
            yaml.dump({'removeStrategy': data['removeStrategy'], 'items': items}, f)

if getattr(sys, 'frozen', False):
    bundleutils(sys.argv[1:])