from enum import Enum, auto
import json
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
import importlib.resources as pkg_resources
from importlib.metadata import version as app_version, PackageNotFoundError
from collections import defaultdict
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq
from server_management.server_manager import JenkinsServerManager

locale.setlocale(locale.LC_ALL, "C")

yaml = YAML(typ='rt')

script_name = os.path.basename(__file__).replace('.py', '')
script_name_upper = script_name.upper()

plugin_json_url_path = '/manage/pluginManager/api/json?pretty&depth=1&tree=plugins[*[*]]'
fetch_url_path = '/core-casc-export'
validate_url_path = '/casc-bundle-mgnt/casc-bundle-validate'

default_target = 'target/docs'
default_normalized = default_target + '-normalized'
default_auto_env_file = 'bundle-profiles.yaml'

# environment variables
BUNDLEUTILS_CI_VERSION = 'BUNDLEUTILS_CI_VERSION'
BUNDLEUTILS_CI_TYPE = 'BUNDLEUTILS_CI_TYPE'
BUNDLEUTILS_CI_SERVER_HOME = 'BUNDLEUTILS_CI_SERVER_HOME'
BUNDLEUTILS_LOG_LEVEL = 'BUNDLEUTILS_LOG_LEVEL'
BUNDLEUTILS_AUTO_ENV_FILE = 'BUNDLEUTILS_AUTO_ENV_FILE'
BUNDLEUTILS_ENV = 'BUNDLEUTILS_ENV'
BUNDLEUTILS_ENV_OVERRIDE = 'BUNDLEUTILS_ENV_OVERRIDE'
BUNDLEUTILS_USE_PROFILE = 'BUNDLEUTILS_USE_PROFILE'
BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR = 'BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR'
BUNDLEUTILS_BOOTSTRAP_PROFILE = 'BUNDLEUTILS_BOOTSTRAP_PROFILE'
BUNDLEUTILS_BOOTSTRAP_UPDATE = 'BUNDLEUTILS_BOOTSTRAP_UPDATE'
BUNDLEUTILS_SETUP_SOURCE_DIR = 'BUNDLEUTILS_SETUP_SOURCE_DIR'
BUNDLEUTILS_VALIDATE_SOURCE_DIR = 'BUNDLEUTILS_VALIDATE_SOURCE_DIR'
BUNDLEUTILS_TRANSFORM_SOURCE_DIR = 'BUNDLEUTILS_TRANSFORM_SOURCE_DIR'
BUNDLEUTILS_TRANSFORM_TARGET_DIR = 'BUNDLEUTILS_TRANSFORM_TARGET_DIR'
BUNDLEUTILS_TRANSFORM_CONFIGS = 'BUNDLEUTILS_TRANSFORM_CONFIGS'
BUNDLEUTILS_BUNDLE_DESCRIPTION = 'BUNDLEUTILS_BUNDLE_DESCRIPTION'
BUNDLEUTILS_JENKINS_URL = 'BUNDLEUTILS_JENKINS_URL'
BUNDLEUTILS_USERNAME = 'BUNDLEUTILS_USERNAME'
BUNDLEUTILS_PASSWORD = 'BUNDLEUTILS_PASSWORD'
BUNDLEUTILS_PATH = 'BUNDLEUTILS_PATH'
BUNDLEUTILS_FETCH_TARGET_DIR = 'BUNDLEUTILS_FETCH_TARGET_DIR'
BUNDLEUTILS_FETCH_OFFLINE = 'BUNDLEUTILS_FETCH_OFFLINE'
BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE = 'BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE'
BUNDLEUTILS_PLUGINS_JSON_PATH = 'BUNDLEUTILS_PLUGINS_JSON_PATH'
BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY = 'BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY'
BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY = 'BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY'
BUNDLEUTILS_BUNDLES_DIR = 'BUNDLEUTILS_BUNDLES_DIR'
BUNDLEUTILS_CREDENTIAL_DELETE_SIGN = 'PLEASE_DELETE_ME'

# context object keys
BUNDLE_PROFILES = 'BUNDLE_PROFILES'
ORIGINAL_CWD = 'ORIGINAL_CWD'

# click ctx object keys
ENV_FILE_ARG = 'env_file'
INTERACTIVE_ARG = 'interactive'
BUNDLES_DIR_ARG = 'bundles_dir'
CI_VERSION_ARG = 'ci_version'
CI_TYPE_ARG = 'ci_type'
CI_SERVER_HOME_ARG = 'ci_server_home'
SOURCE_DIR_ARG = 'source_dir'
TARGET_DIR_ARG = 'target_dir'
PLUGIN_JSON_ADDITIONS_ARG = 'plugin_json_additions'
PLUGIN_JSON_URL_ARG = 'plugin_json_url'
PLUGIN_JSON_PATH_ARG = 'plugin_json_path'
PATH_ARG = 'path'
URL_ARG = 'url'
USERNAME_ARG = 'username'
PASSWORD_ARG = 'password'


def die(msg):
    logging.error(f"{msg}\n")
    sys.exit(1)

class PluginJsonMergeStrategy(Enum):
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

def get_value_from_enum(value, my_enum):
    try:
        return my_enum[value]
    except KeyError:
        die(f"Invalid value: {value} for {my_enum}. Must be one of {[e.name for e in my_enum]}")

def get_name_from_enum(my_enum):
    return [x.name for x in my_enum]


def common_options(func):
    func = click.option('-l', '--log-level', default=os.environ.get(BUNDLEUTILS_LOG_LEVEL, 'INFO'), help=f'The log level (or use {BUNDLEUTILS_LOG_LEVEL}).')(func)
    func = click.option('-e', '--env-file', default=os.environ.get(BUNDLEUTILS_ENV, ''), type=click.Path(file_okay=True, dir_okay=False), help=f'Optional bundle profiles file (or use {BUNDLEUTILS_ENV}).')(func)
    func = click.option('-i', '--interactive', default=False, is_flag=True, help=f'Run in interactive mode.')(func)
    return func

def server_options(func):
    func = click.option('-v', '--ci-version', type=click.STRING, help=f'The version of the CloudBees WAR file.')(func)
    func = click.option('-t', '--ci-type', type=click.STRING, help=f'The type of the CloudBees server.')(func)
    func = click.option('-H', '--ci-server-home', required=False, help=f'Defaults to /tmp/ci_server_home/<ci_type>/<ci_version>.')(func)
    return func

def fetch_options(func):
    func = click.option('-M', '--plugin-json-path', help=f'The path to fetch JSON file from (found at {plugin_json_url_path}).')(func)
    func = click.option('-P', '--path', 'path', type=click.Path(file_okay=True, dir_okay=False), help=f'The path to fetch YAML from (or use {BUNDLEUTILS_PATH}).')(func)
    func = click.option('-c', '--cap', default=False, is_flag=True, help=f'Use the envelope.json from the war file to remove CAP plugin dependencies (or use {BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE}).')(func)
    func = click.option('-O', '--offline', default=False, is_flag=True, help=f'Save the export and plugin data to <target-dir>-offline (or use {BUNDLEUTILS_FETCH_OFFLINE}).')(func)
    func = click.option('-j', '--plugins-json-list-strategy', help=f'Strategy for creating list from the plugins json (or use {BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY}).')(func)
    func = click.option('-J', '--plugins-json-merge-strategy', help=f'Strategy for merging plugins from list into the bundle (or use {BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY}).')(func)
    func = click.option('-U', '--url', 'url', help=f'The URL to fetch YAML from (or use {BUNDLEUTILS_JENKINS_URL}).')(func)
    func = click.option('-u', '--username', help=f'Username for basic authentication (or use {BUNDLEUTILS_USERNAME}).')(func)
    func = click.option('-p', '--password', help=f'Password for basic authentication (or use {BUNDLEUTILS_PASSWORD}).')(func)
    func = click.option('-t', '--target-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory for the YAML documents (or use {BUNDLEUTILS_FETCH_TARGET_DIR}).')(func)
    return func


def server_options_null_check(ci_version, ci_type, ci_server_home):
    ci_version = null_check(ci_version, CI_VERSION_ARG, BUNDLEUTILS_CI_VERSION)
    ci_type = null_check(ci_type, CI_TYPE_ARG, BUNDLEUTILS_CI_TYPE)
    ci_server_home = null_check(ci_server_home, CI_SERVER_HOME_ARG, BUNDLEUTILS_CI_SERVER_HOME, False)
    return ci_version, ci_type, ci_server_home

def transform_options(func):
    func = click.option('-S', '--strict', default=False, is_flag=True, help=f'Fail when referencing non-existent files - warn otherwise.')(func)
    func = click.option('-c', '--config', 'configs', multiple=True, help=f'The transformation config(s).')(func)
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

def _check_cwd_for_bundle_auto_vars(ctx):
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
    bundle_name = os.path.basename(cwd)

    # if the cwd is a subdirectory of auto_env_file_path_dir, create a relative path
    bundle_target_dir = cwd
    if cwd.startswith(auto_env_file_path_dir):
        bundle_target_dir = os.path.relpath(cwd, auto_env_file_path_dir)
    logging.debug(f'Current working directory: {cwd}')
    logging.debug(f'Switching to the base directory of env file: {auto_env_file_path_dir}')
    os.chdir(auto_env_file_path_dir)

    # if the cwd contains a file bundle.yaml
    adhoc_profile = os.environ.get(BUNDLEUTILS_USE_PROFILE, '')
    if adhoc_profile:
        logging.info(f'Found env var {BUNDLEUTILS_USE_PROFILE}: {adhoc_profile}')
        if adhoc_profile in bundle_profiles['profiles']:
            logging.info(f'Using adhoc bundle config for {bundle_name}')
            env_vars = bundle_profiles['profiles'][adhoc_profile]
        else:
            die(f'No bundle profile found for {adhoc_profile}')
    else:
        if bundle_name in bundle_profiles['bundles']:
            logging.info(f'Found bundle config for {bundle_name}')
            env_vars = bundle_profiles['bundles'][bundle_name]
        else:
            logging.info(f'No bundle config found for {bundle_name} and no {BUNDLEUTILS_USE_PROFILE} set')

    if env_vars:
        # check if the BUNDLEUTILS_ENV_OVERRIDE is set to true, if so, override the env vars
        should_env_vars_override_others = os.environ.get(BUNDLEUTILS_ENV_OVERRIDE, 'false').lower() in ['true', '1', 't', 'y', 'yes']
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
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_FETCH_TARGET_DIR, f'target/docs-{bundle_name}')
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_TRANSFORM_SOURCE_DIR, os.environ.get(BUNDLEUTILS_FETCH_TARGET_DIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_TRANSFORM_TARGET_DIR, bundle_target_dir)
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_SETUP_SOURCE_DIR, os.environ.get(BUNDLEUTILS_TRANSFORM_TARGET_DIR))
        _set_env_if_not_set('AUTOSET', BUNDLEUTILS_VALIDATE_SOURCE_DIR, os.environ.get(BUNDLEUTILS_TRANSFORM_TARGET_DIR))

def set_logging(ctx):
    _check_for_env_file(ctx)
    _check_cwd_for_bundle_auto_vars(ctx)

@click.group(invoke_without_command=True)
@common_options
@click.pass_context
def cli(ctx, log_level, env_file, interactive):
    """A tool to fetch and transform YAML documents."""
    ctx.ensure_object(dict)
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

def null_check(obj, obj_name, obj_env_var=None, mandatory=True, default=''):
    if not obj:
        if obj_env_var:
            obj = os.environ.get(obj_env_var, '')
            if not obj:
                if default:
                    obj = default
                elif mandatory:
                    die(f'No {obj_name} option provided and no {obj_env_var} set')
    return obj

def lookup_url_and_version(url, ci_version, default_url = '', default_ci_version = ''):
    url = null_check(url, URL_ARG, 'JENKINS_URL', True, default_url)
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

@cli.command()
@click.pass_context
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be bootstrapped.')
@click.option('-p', '--profile', help=f'The bundle profile to use.')
@click.option('-u', '--update', help=f'Should the bundle be updated if present.')
@click.option('-U', '--url', help=f'The controller URL to bootstrap (or use JENKINS_URL).')
@click.option('-v', '--ci-version', type=click.STRING, help=f'Optional version (taken from the remote instance otherwise).')
def bootstrap(ctx, source_dir, profile, update, url, ci_version):
    """Bootstrap a bundle"""
    _check_for_env_file(ctx)
    # no bundle_profiles found, no need to check
    if not ctx.obj.get(BUNDLE_PROFILES, ''):
        logging.debug('No bundle profiles found. Nothing to add the bundle to.')
        return

    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_BOOTSTRAP_SOURCE_DIR)
    bootstrap_profile = null_check(profile, 'profile', BUNDLEUTILS_BOOTSTRAP_PROFILE)
    bootstrap_update = null_check(update, 'update', BUNDLEUTILS_BOOTSTRAP_UPDATE, False, 'false')
    if bootstrap_profile:
        bundle_profiles = ctx.obj.get(BUNDLE_PROFILES)
        bundle_name = os.path.basename(source_dir)
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

@cli.command()
@server_options
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be validated (startup will use the plugins from here).')
@click.option('-T', '--ci-bundle-template', type=click.Path(file_okay=False, dir_okay=True), required=False, help=f'Path to a template bundle used to start the test server (defaults to in-built tempalte).')
@click.pass_context
def ci_setup(ctx, ci_version, ci_type, ci_server_home, source_dir, ci_bundle_template):
    """Download CloudBees WAR file, and setup the starter bundle"""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_SETUP_SOURCE_DIR)
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
    jenkins_manager.get_war()
    jenkins_manager.create_startup_bundle(plugin_files, ci_bundle_template)
    _update_bundle(jenkins_manager.target_jenkins_home_casc_startup_bundle)

@cli.command()
@server_options
@click.option('-s', '--source-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The bundle to be validated.')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help=f'Do not fail if warnings are found.')
@click.pass_context
def ci_validate(ctx, ci_version, ci_type, ci_server_home, source_dir, ignore_warnings):
    """Validate bundle against controller started with ci-start."""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_VALIDATE_SOURCE_DIR)
    if not os.path.exists(source_dir):
        die(f"Source directory '{source_dir}' does not exist")
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    logging.debug(f"Server URL: {server_url}, Username: {username}, Password: {password}")
    _validate(server_url, username, password, source_dir, ignore_warnings)

@cli.command()
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

@cli.command()
@server_options
@click.pass_context
def ci_start(ctx, ci_version, ci_type, ci_server_home):
    """Start CloudBees Server"""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.start_server()

@cli.command()
@server_options
@click.pass_context
def ci_stop(ctx, ci_version, ci_type, ci_server_home):
    """Stop CloudBees Server"""
    set_logging(ctx)
    ci_version, ci_type, ci_server_home = server_options_null_check(ci_version, ci_type, ci_server_home)
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.stop_server()

# add a diff command to diff two directories by calling the diff command on each file
@cli.command()
@click.argument('src1', type=click.Path(exists=True))
@click.argument('src2', type=click.Path(exists=True))
@click.pass_context
def diff(ctx, src1, src2):
    """Diff two YAML directories or files."""
    set_logging(ctx)
    diff_detected = False
    # if src1 is a directory, ensure src2 is also directory
    if os.path.isdir(src1) and os.path.isdir(src2):
        files1 = os.listdir(src1)
        files2 = os.listdir(src2)
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
    elif os.path.isfile(src1) and os.path.isfile(src2):
        if diff2(src1, src2):
            diff_detected = True
    else:
        die("src1 and src2 must both be either directories or files")
    if diff_detected:
        die("Differences detected")

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

@cli.command()
@click.pass_context
def config(ctx):
    """List evaluated config based on cwd and env file."""

    set_logging(ctx)
    # loop through all the environment variables, sorted alphabetically, starting with BUNDLEUTILS_ and print them as a single multiline string
    logging.info("Evaluated configuration:")
    lines = []
    for key, value in sorted(os.environ.items()):
        if key.startswith('BUNDLEUTILS_'):
            lines.append(f'{key}={value}')
    click.echo('\n'.join(lines))

@cli.command()
def version():
    """Show the app version."""
    try:
        package_name = 'bundleutilspkg'
        pkg_version = app_version(package_name)
        click.echo(f"Built with commit: {pkg_version}")
    except PackageNotFoundError:
        click.echo("Package is not installed. Please ensure it's built and installed correctly.")

@cli.command()
@click.option('-U', '--url', help=f'The controller URL to test for (or use JENKINS_URL).')
@click.option('-v', '--ci-version', type=click.STRING, help=f'Optional version (taken from the remote instance otherwise).')
@click.option('-b', '--bundles-dir', type=click.Path(file_okay=False, dir_okay=True), help=f'The directory containing the bundles.')
@click.pass_context
def find_bundle_by_url(ctx, url, ci_version, bundles_dir):
    """Find a bundle by Jenkins URL and CI Version."""
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
        if bundle_env_vars.get(BUNDLEUTILS_JENKINS_URL, '').strip().rstrip('/') == url.strip().rstrip('/') and bundle_env_vars.get(BUNDLEUTILS_CI_VERSION, '') == ci_version:
            logging.debug(f"Found bundle: {bundle_name}. Checking for bundle.yaml in {bundles_dir}")
            bundles_found = []
            for bundle_found in glob.iglob(f'{bundles_dir}/**/{bundle_name}/bundle.yaml', recursive=True):
                logging.debug(f"Found bundle.yaml: {bundle_found}")
                bundles_found.append(bundle_found)
                if my_bundle:
                    # exit with exit code 1 and text message if a second bundle is found
                    die(f"Multiple bundles found matching the criteria: {my_bundle} and {bundle_found}")

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
@cli.command()
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
    if not obj:
        if obj_env_var:
            obj = os.environ.get(obj_env_var, '')
            if not obj:
                if default:
                    obj = default
                if ctx.obj.get(INTERACTIVE_ARG):
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
    logging.debug(f'Setting ctx - > {obj_name}: {obj}')
    ctx.obj[obj_name] = obj
    return obj

@cli.command()
@click.option('-U', '--url', help=f'The controller URL to validate agianst (or use {BUNDLEUTILS_JENKINS_URL}).')
@click.option('-u', '--username', help=f'Username for basic authentication (or use {BUNDLEUTILS_USERNAME}).')
@click.option('-p', '--password', help=f'Password for basic authentication (or use {BUNDLEUTILS_PASSWORD}).')
@click.option('-s', '--source-dir', required=True, type=click.Path(file_okay=False, dir_okay=True), help=f'The source directory for the YAML documents (or use {BUNDLEUTILS_VALIDATE_SOURCE_DIR}).')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help=f'Do not fail if warnings are found.')
@click.pass_context
def validate(ctx, url, username, password, source_dir, ignore_warnings):
    """Validate bundle in source dir against URL."""
    set_logging(ctx)
    _validate(url, username, password, source_dir, ignore_warnings)

def _validate(url, username, password, source_dir, ignore_warnings):
    username = null_check(username, 'username', BUNDLEUTILS_USERNAME)
    password = null_check(password, 'password', BUNDLEUTILS_PASSWORD)
    source_dir = null_check(source_dir, 'source directory', BUNDLEUTILS_VALIDATE_SOURCE_DIR)
    url = null_check(url, URL_ARG, BUNDLEUTILS_JENKINS_URL)
    # if the url does end with /casc-bundle-mgnt/casc-bundle-validate, append it
    if validate_url_path not in url:
        url = url + validate_url_path

    # fetch the YAML from the URL
    headers = { 'Content-Type': 'application/zip' }
    if username and password:
        headers['Authorization'] = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
    # zip and post the YAML to the URL
    with zipfile.ZipFile('bundle.zip', 'w') as zip_ref:
        for filename in os.listdir(source_dir):
            zip_ref.write(os.path.join(source_dir, filename), filename)
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
def fetch_options_null_check(ctx, url, path, username, password, target_dir, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, offline, cap):
    # creds boolean True if URL set and not empty
    creds_needed = url is not None and url != ''
    cap = null_check(cap, 'cap', BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE, False, '')
    offline = null_check(offline, 'offline', BUNDLEUTILS_FETCH_OFFLINE, False, '')
    url = null_check(url, 'url', BUNDLEUTILS_JENKINS_URL, False)
    # fail fast if any strategy is passed explicitly
    default_plugins_json_list_strategy = PluginJsonListStrategy.AUTO
    default_plugins_json_merge_strategy = PluginJsonMergeStrategy.ADD_DELETE_SKIP_PINNED
    plugins_json_list_strategy = null_check(plugins_json_list_strategy, 'plugins_json_list_strategy', BUNDLEUTILS_PLUGINS_JSON_LIST_STRATEGY, True, default_plugins_json_list_strategy)
    plugins_json_merge_strategy = null_check(plugins_json_merge_strategy, 'plugins_json_merge_strategy', BUNDLEUTILS_PLUGINS_JSON_MERGE_STRATEGY, True, default_plugins_json_merge_strategy)
    username = null_check(username, USERNAME_ARG, BUNDLEUTILS_USERNAME, creds_needed)
    password = null_check(password, PASSWORD_ARG, BUNDLEUTILS_PASSWORD, creds_needed)
    path = null_check(path, PATH_ARG, BUNDLEUTILS_PATH, False)
    plugin_json_path = null_check(plugin_json_path, PLUGIN_JSON_PATH_ARG, BUNDLEUTILS_PLUGINS_JSON_PATH, False)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_FETCH_TARGET_DIR, False, default_target)
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

@cli.command()
@fetch_options
@click.pass_context
def fetch(ctx, url, path, username, password, target_dir, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, offline, cap):
    """Fetch YAML documents from a URL or path."""
    set_logging(ctx)
    fetch_options_null_check(url, path, username, password, target_dir, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, offline, cap)
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
    logging.info(f"{prefix}Start...")
    # check in the jenkins.yaml file for the key 'cascItemsConfiguration.variableInterpolationEnabledForAdmin'
    jenkins_yaml = os.path.join(target_dir, 'jenkins.yaml')
    if not os.path.exists(jenkins_yaml):
        die(f"Jenkins YAML file '{jenkins_yaml}' does not exist (something seriously wrong here)")
    with open(jenkins_yaml, 'r') as f:
        jenkins_data = yaml.load(f)
    if 'cascItemsConfiguration' in jenkins_data['unclassified'] and 'variableInterpolationEnabledForAdmin' in jenkins_data['unclassified']['cascItemsConfiguration']:
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
            items_data = replace_string_in_dict(items_data, pattern, search_replace)
            prefix = 'EQUAL DISPLAY_NAME CHECK: '
            logging.info(f"{prefix}Start...")
            items_data = replace_display_name_if_necessary(items_data)
            logging.info(f"{prefix}Finished...")
        with open(items_yaml, 'w') as f:
                yaml.dump(items_data, f)

def replace_display_name_if_necessary(data):
    if isinstance(data, dict):
        # if dict has key 'displayName' and 'name' and they are the same, remove the 'displayName' key
        if 'displayName' in data and 'name' in data and data['displayName'] == data['name']:
            logging.info(f"Setting 'displayName' to empty string since equal to name: {data['name']}")
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

def replace_string_in_dict(data, pattern, replacement):
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                data[key] = replace_string_in_dict(value, pattern, replacement)
            elif isinstance(value, list):
                data[key] = replace_string_in_list(value, pattern, replacement)
            elif isinstance(value, str):
                match = re.search(pattern, value)
                if match:
                    logging.debug(f"Replacing '{pattern}' with '{replacement}' in dict '{value}'")
                    data[key] = re.sub(pattern, replacement, value)
    return data

def replace_string_in_list(data, pattern, replacement):
    for i, value in enumerate(data):
        if isinstance(value, dict):
            data[i] = replace_string_in_dict(value, pattern, replacement)
        elif isinstance(value, list):
            data[i] = replace_string_in_list(value, pattern, replacement)
        elif isinstance(value, str):
            match = re.search(pattern, value)
            if match:
                logging.debug(f"Replacing '{pattern}' with '{replacement}' in list '{value}'")
                data[i] = re.sub(pattern, replacement, value)
    return data

def show_diff(title, plugins, col1, col2):
    hline(f"DIFF: {title}")
    for plugin in plugins:
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

@click.pass_context
def _analyze_server_plugins(ctx, plugins_from_json):
    plugins_json_list_strategy = ctx.obj.get('plugins_json_list_strategy')
    cap = ctx.obj.get('cap')
    logging.debug("Plugin Analysis - Analyzing server plugins...")
    # Setup the dependency graphs
    graphs = {}
    graph_type_all = 'all'
    graph_type_minus_bootstrap = 'minus-bootstrap'
    graph_type_minus_deleted_disabled = 'minus-deleted-disabled'
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

    # Function to find all plugins with `pluginX` in their dependency tree
    def plugins_with_plugin_in_tree(graph_type, target_plugin):
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
        expected_plugins = dgall.keys()
    else:
        die(f"Invalid plugins json list strategy: {plugins_json_list_strategy.name}. Expected one of: {PluginJsonListStrategy}")

    # handle the removal of CAP plugin dependencies removal
    if cap:
        logging.info(f"{BUNDLEUTILS_FETCH_USE_CAP_ENVELOPE} option detected. Removing CAP plugin dependencies...")
        expected_plugins_copy = expected_plugins.copy()
        url, ci_version = lookup_url_and_version('', '')
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
    return expected_plugins, all_bootstrap_plugins, all_deleted_or_inactive_plugins

def find_plugin_by_id(plugins, plugin_id):
    logging.debug(f"Finding plugin by id: {plugin_id}")
    for plugin in plugins:
        if plugin.get('id') == plugin_id:
            return plugin
    return None

@cli.command()
@fetch_options
@click.pass_context
def update_plugins(ctx, url, path, username, password, target_dir, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, offline, cap):
    """Update plugins in the target directory."""
    set_logging(ctx)
    fetch_options_null_check(url, path, username, password, target_dir, plugin_json_path, plugins_json_list_strategy, plugins_json_merge_strategy, offline, cap)
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
                elif api_version == '1':
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS_AND_DEPS
                    ctx.obj['plugins_json_list_strategy'] = plugins_json_list_strategy
                elif api_version == '2':
                    plugins_json_list_strategy = PluginJsonListStrategy.ROOTS
                    ctx.obj['plugins_json_list_strategy'] = plugins_json_list_strategy
                else:
                    die(f"Invalid apiVersion found in bundle.yaml file: {api_version}")
                logging.info(f'Setting plugins_json_list_strategy to {plugins_json_list_strategy.name} from {get_name_from_enum(PluginJsonListStrategy)} based on apiVersion {api_version} in bundle.yaml')

    # load the plugin JSON from the URL or path
    data = None
    if plugin_json_path:
        logging.debug(f'Loading plugin JSON from path: {plugin_json_path}')
        with open(plugin_json_path, 'r') as f:
            data = json.load(f)
    elif url:
        plugin_json_url = url + plugin_json_url_path
        logging.debug(f'Loading plugin JSON from URL: {plugin_json_url}')
        response_text = call_jenkins_api(plugin_json_url, username, password)
        if offline:
            with open(export_json, 'w') as f:
                logging.info(f'[offline] Writing plugins.json to {export_json}')
                f.write(response_text)
        # parse text as JSON
        data = json.loads(response_text)
    else:
        logging.info('No plugin JSON URL or path provided. Cannot determine if disabled/deleted plugins present in list.')
        return
    plugins_from_json = data.get("plugins", [])
    expected_plugins, all_bootstrap_plugins, all_deleted_or_inactive_plugins = _analyze_server_plugins(plugins_from_json)

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
                logging.info(f" -> removing unexpected bootstrap plugin {plugin['id']}")
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
                        logging.info(f" -> removing unexpected non-pinned plugin {plugin['id']} according to merge strategy: {plugins_json_merge_strategy.name}")
                elif plugins_json_merge_strategy.should_delete:
                    logging.info(f" -> removing unexpected plugin {plugin['id']} according to merge strategy: {plugins_json_merge_strategy.name}")
                else:
                    logging.warning(f" -> unexpected plugin {plugin['id']} found but not removed according to merge strategy: {plugins_json_merge_strategy.name}")
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
        all_plugin_ids = updated_plugins_ids + expected_plugins
        show_diff("Final merged plugins < vs > expected plugins after merging", all_plugin_ids, updated_plugins_ids, expected_plugins)
        if plugin_catalog_plugin_ids_previous:
            show_diff("Final merged catalog < vs > previous catalog after merging", plugin_catalog_plugin_ids + plugin_catalog_plugin_ids_previous, plugin_catalog_plugin_ids, plugin_catalog_plugin_ids_previous)

        plugins_data['plugins'] = updated_plugins
        if plugins_json_merge_strategy == PluginJsonMergeStrategy.DO_NOTHING:
            logging.info(f"Skipping writing to plugins.yaml according to merge strategy: {plugins_json_merge_strategy.name}")
        else:
            with open(plugins_file, 'w') as f:
                yaml.dump(plugins_data, f)  # Write the updated data back to the file

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
                            response_text = replace_carriage_returns(response_text)
                            logging.debug(f'Read YAML from file: {filename}')
                            doc = yaml.load(response_text)
                            write_yaml_doc(doc, target_dir, filename)
                        else:
                            logging.warning(f'Skipping empty file: {filename}')
        else:
            logging.info(f'Read YAML from path: {path}')
            with open(path, 'r') as f:
                response_text = f.read()
                response_text = replace_carriage_returns(response_text)
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
        response_text = replace_carriage_returns(response_text)
        # logging.debug(f'Fetched YAML from url {url}:\n{response_text}')
        yaml_docs = list(yaml.load_all(response_text))
        write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    else:
        die('No path or URL provided')

def replace_carriage_returns(response_text):
        if isinstance(response_text, bytes):
            response_text = response_text.decode('utf-8')
        # print any lines with carriage returns in them
        for line in response_text.split('\n'):
            if '\\r' in line:
                logging.debug(f'Carriage return found in line: {line}')
        # remove any '\r' characters from the response
        logging.info('Removing carriage returns from the response')
        response_text = response_text.replace('\\r', '')
        # print any lines with carriage returns in them
        for line in response_text.split('\n'):
            if '\\r' in line:
                logging.warn(f'Carriage return found in line still: {line}')
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
        # remove comments from the YAML doc
        doc.ca.comment = None
        write_yaml_doc(doc, target_dir, filename)

def write_yaml_doc(doc, target_dir, filename):
    filename = os.path.join(target_dir, filename)
    # normalize the YAML doc
    doc = normalize_yaml(doc)
    doc = remove_empty_keys(doc)

    # create a new file for each YAML document
    logging.debug(f'Creating {filename}')
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

# TODO: remove after testing with normalising
def normalize_yaml(data):
    """Normalize a nested dictionary."""
    if isinstance(data, dict):
        return {k: normalize_yaml(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [normalize_yaml(v) for v in data]
    elif isinstance(data, str):
        # Normalize strings that contain newline characters
        # if '\\n' in data:
        #     return '|\n' + data.replace('\\n', '\n')
        # else:
            return data
    else:
        return data

def traverse_credentials(filename, obj, custom_replacements={}, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else f"/{k}"
            # does custom_replacements contain an id that matches the id in the object and a key matching k?
            if isinstance(v, str) and 'id' in obj:
                id = obj['id']
                matching_tuple = None
                custom_replacements_for_id = [item for item in custom_replacements if item['id'] == id]
                for custom_replacement in custom_replacements_for_id:
                    if k in custom_replacement:
                        matching_tuple = custom_replacement
                if re.match(r'{.*}', v) or matching_tuple is not None:
                    if matching_tuple is None or k not in matching_tuple:
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
            traverse_credentials(filename, v, custom_replacements, new_path)
    elif isinstance(obj, list):
        # traverse the list in reverse order to avoid index issues when deleting items
        for i, v in enumerate(reversed(obj)):
            # Calculate the original index by subtracting the reversed index from the length of the list minus 1
            original_index = len(obj) - 1 - i
            new_path = f"{path}/{original_index}"
            traverse_credentials(filename, v, custom_replacements, new_path)
    else:
        if isinstance(obj, str) and re.match(r'{.*}', obj):
            # if the string is a replacement string, raise an exception
            logging.warning(f"Found a non-credential string (no id found) that needs to be replaced at path: {path}")
            # the replacement string should be in the format ${ID_KEY}
            replacement = "${" + re.sub(r'\W', '_', path.removeprefix('/')).upper() + "}"
            # print the JSON Patch operation for the replacement
            patch = {"op": "replace", "path": f'{path}', "value": f'{replacement}'}
            apply_patch(filename, [patch])

def apply_patch(filename, patch_list):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)

    if obj is None:
        logging.error(f'Failed to load YAML object from file {filename}')
        return

    # for each patch, apply the patch to the object
    for patch in patch_list:
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
        logging.info(f'Transform: applying JSON patches to {filename}')
        apply_patch(filename, patch)

def apply_replacements(filename, custom_replacements):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)
        if obj is None:
            logging.error(f'Failed to load YAML object from file {filename}')
            return
        traverse_credentials(filename, obj, custom_replacements)

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

def printYaml(obj):
    stream = io.StringIO()
    yaml.dump(obj, stream)
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


@cli.command()
@transform_options
@click.pass_context
def normalize(ctx, strict, configs, source_dir, target_dir):
    """Transform using the normalize.yaml for better comparison."""
    set_logging(ctx)
    if not source_dir:
        source_dir = default_target
    if not target_dir:
        target_dir = default_normalized
    if not configs:
        # if a normalize.yaml file is found in the current directory, use it
        if os.path.exists('normalize.yaml'):
            logging.info('Using normalize.yaml in the current directory')
            configs = ['normalize.yaml']
        else:
            path = pkg_resources.files('defaults.configs') / 'normalize.yaml'
            configs = [path]
    _transform(configs, source_dir, target_dir)

@cli.command()
@transform_options
@click.pass_context
def transform(ctx, strict, configs, source_dir, target_dir):
    """Transform using a custom transformation config."""
    set_logging(ctx)
    source_dir = null_check(source_dir, SOURCE_DIR_ARG, BUNDLEUTILS_TRANSFORM_SOURCE_DIR)
    target_dir = null_check(target_dir, TARGET_DIR_ARG, BUNDLEUTILS_TRANSFORM_TARGET_DIR)
    configs = null_check(configs, 'configs', BUNDLEUTILS_TRANSFORM_CONFIGS, False)
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
    _transform(configs, source_dir, target_dir)

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

def _transform(configs, source_dir, target_dir):
    """Transform using a custom transformation config."""
    # add the transformation configs recursively into the merged config
    merged_config = {}
    for config in configs:
        _file_check(config, True)
        with open(config, 'r') as inp:
            logging.info(f'Transformation: processing {config}')
            obj = yaml.load(inp)
            merged_config = recursive_merge(merged_config, obj)

    logging.debug(f'Merged config:\n' + printYaml(merged_config))
    # if the target directory is not set, use the source directory suffixed with -transformed
    if not target_dir:
        target_dir = source_dir + '-transformed'
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
        with open(source_filename, 'r') as inp:
            obj = yaml.load(inp)
        with open(target_filename, 'w') as out:
            yaml.dump(obj, out)

    handle_patches(merged_config.get('patches', {}), target_dir)
    handle_credentials(merged_config.get('credentials', []), target_dir)
    handle_substitutions(merged_config.get('substitutions', {}), target_dir)
    handle_splits(merged_config.get('splits', {}), target_dir)
    _update_bundle(target_dir)

def remove_empty_keys(data):
    if isinstance(data, dict):  # If the data is a dictionary
        # Create a new dictionary, skipping entries with empty keys
        ret = {k: remove_empty_keys(v) for k, v in data.items() if k != ""}
        logging.log(logging.NOTSET, f'Removing empty keys from DICT {data}')
        logging.log(logging.NOTSET, f'Result: {ret}')
        return ret
    elif isinstance(data, list):  # If the data is a list
        logging.log(logging.NOTSET, f'Removing empty keys from LIST {data}')
        newdata = []
        for v in data:
            ret = remove_empty_keys(v)
            if ret:
                newdata.append(ret)
        logging.log(logging.NOTSET, f'Result: {newdata}')
        return newdata
    else:
        # Return the item itself if it's not a dictionary or list
        return data

@cli.command()
@click.option('-t', '--target-dir', 'target_dir', required=True, type=click.Path(file_okay=False, dir_okay=True), help=f'The target directory to update the bundle.yaml file.')
@click.option('-d', '--description', 'description', help=f'Optional description for the bundle (also {BUNDLEUTILS_BUNDLE_DESCRIPTION}).')
@click.pass_context
def update_bundle(ctx, target_dir, description):
    """Update the bundle.yaml file in the target directory."""
    set_logging(ctx)
    _update_bundle(target_dir, description)

def _update_bundle(target_dir, description=None):
    description = null_check(description, 'description', BUNDLEUTILS_BUNDLE_DESCRIPTION, False)
    keys = ['jcasc', 'items', 'plugins', 'rbac', 'catalog', 'variables']

    logging.info(f'Updating bundle in {target_dir}')
    # Load the YAML file
    with open(os.path.join(target_dir, 'bundle.yaml'), 'r') as file:
        data = yaml.load(file)

    all_files = []
    # Iterate over the keys
    for key in keys:
        files = []
        # Special case for 'jcasc'
        if key == 'jcasc':
            prefixes = ['jenkins', 'jcasc']
        elif key == 'catalog':
            prefixes = ['plugin-catalog']
        else:
            prefixes = [key]

        # if prefix.yaml exists, add
        exact_match = None
        for prefix in prefixes:
            exact_match = os.path.join(target_dir, f'{prefix}.yaml')
            if os.path.exists(exact_match):
                files = [exact_match]
                break

        # Add list of YAML files starting with the prefix
        for prefix in prefixes:
            files += sorted(glob.glob(os.path.join(target_dir, f'{prefix}.*.yaml')))
        # remove any empty files
        files = [file for file in files if _file_check(file)]

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

        # Remove the target_dir path and sort the files, ensuring exact match come first
        files = [os.path.basename(file) for file in files]

        # if no files found, remove the key from the data if it exists
        if not files:
            if key in data:
                logging.info(f'Removing key {key} from the bundle as no files were found')
                del data[key]
            continue

        # Update the key in the data
        data[key] = files

        # Add the files to the all_files list
        all_files.extend(files)

    # update the id key with the basename of the target_dir
    data['id'] = os.path.basename(target_dir)
    data['description'] = f"Bundle for {data['id']}" if not description else description

    # update the version key with the md5sum of the content of all files
    data['version'] = os.popen(f'cat {" ".join([os.path.join(target_dir, file) for file in all_files])} | md5sum').read().split()[0]
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

        # For each path to move...
        for path in paths:

            # Check if the path exists in the source file
            if get_nested(source_data, path) is not None:
                # Determine the target file name
                if target == 'auto':
                    target_file = path.replace('/', '.') + '.yaml'
                else:
                    target_file = target
                target_file = os.path.join(target_dir, 'jenkins.' + target_file)
                logging.info(f'Moving {path} to {target_file}')

                # Load the target file if it exists, or create a new one if it doesn't
                if os.path.exists(target_file):
                    logging.info(f'Loading existing target file {target_file}')
                    with open(target_file, 'r') as file:
                        target_data = yaml.load(file)
                else:
                    logging.info(f'Creating new target file {target_file}')
                    target_data = {}

                # Move the path from the source file to the target file
                set_nested(target_data, path, get_nested(source_data, path))
                del_nested(source_data, path)

                # Save the target file
                logging.info(f'Saving target file {target_file}')
                with open(target_file, 'w') as file:
                    yaml.dump(target_data, file)

    # Save the modified source file
    with open(full_filename, 'w') as file:
        yaml.dump(source_data, file)
    # rename the source files base name to "'jenkins.' + filename" if not already done
    if not filename.startswith('jenkins.'):
        new_filename = os.path.join(target_dir, 'jenkins.' + filename)
        logging.info(f'Renaming {full_filename} to {new_filename}')
        os.rename(full_filename, new_filename)

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
