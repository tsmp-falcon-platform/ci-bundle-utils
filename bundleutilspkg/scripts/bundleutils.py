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

default_target = 'target/docs'
default_normalized = default_target + '-normalized'
default_operationalized = default_target + '-operationalized'
default_plugin_json_url = ''
default_fetch_url = ''
default_validate_url = ''
if 'BUNDLEUTILS_JENKINS_URL' in os.environ:
    default_plugin_json_url = os.environ['BUNDLEUTILS_JENKINS_URL'] + '/manage/pluginManager/api/json?pretty&depth=1'
    default_fetch_url = os.environ['BUNDLEUTILS_JENKINS_URL'] + '/core-casc-export'
    default_validate_url = os.environ['BUNDLEUTILS_JENKINS_URL'] + '/casc-bundle-mgnt/casc-bundle-validate'

def common_options(func):
    func = click.option('-l', '--log-level', default=os.environ.get('BUNDLEUTILS_LOG_LEVEL', ''), help='The log level (or use BUNDLEUTILS_LOG_LEVEL).')(func)
    return func

def server_options(func):
    func = click.option('-v', '--ci-version', 'ci_version', default=os.environ.get('BUNDLEUTILS_CI_VERSION', ''), help='The version of the CloudBees WAR file.')(func)
    func = click.option('-t', '--ci-type', 'ci_type', default=os.environ.get('BUNDLEUTILS_CI_TYPE', 'mm'), required=False, type=click.STRING, help='The type of the CloudBees server.')(func)
    func = click.option('-H', '--ci-server-home', 'ci_server_home', required=False, help='Defaults to /tmp/ci_server_home/<ci_type>/<ci_version>.')(func)
    return func

def transform_options(func):
    func = click.option('-S', '--strict', default=False, is_flag=True, help='Fail when refrencing non-existent files. Warn otherwise.')(func)
    func = click.option('-c', '--config', 'configs', multiple=True, default=os.environ.get('BUNDLEUTILS_TRANSFORMATIONS'), help='The transformation config(s) (or use BUNDLEUTILS_TRANSFORMATION).')(func)
    func = click.option('-s', '--source-dir', 'source_dir', default=os.environ.get('BUNDLEUTILS_SOURCE_DIR', ''), type=click.Path(file_okay=False, dir_okay=True), help='The source directory for the YAML documents (or use BUNDLEUTILS_SOURCE_DIR).')(func)
    func = click.option('-t', '--target-dir', 'target_dir', default=os.environ.get('BUNDLEUTILS_TARGET_DIR', ''), type=click.Path(file_okay=False, dir_okay=True), help='The target directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR). Defaults to the source directory suffixed with -transformed.')(func)
    return func

def set_logging(ctx, log_level, default=''):
    if log_level:
        ctx.obj['LOG_LEVEL'] = log_level
    elif default:
        ctx.obj['LOG_LEVEL'] = default
    logging.getLogger().setLevel(ctx.obj['LOG_LEVEL'])

@click.group(invoke_without_command=True)
@common_options
@click.pass_context
def cli(ctx, log_level):
    """A tool to fetch and transform YAML documents."""
    ctx.ensure_object(dict)
    set_logging(ctx, log_level, 'INFO')
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

@cli.command()
@server_options
@click.option('-s', '--source-dir', 'source_dir',  required=True, type=click.Path(file_okay=False, dir_okay=True), help='The bundle to be validated (startup will use the plugins from here).')
@click.option('-T', '--ci-bundle-template', 'bundle_template', type=click.Path(file_okay=False, dir_okay=True), required=False, help='Path to a template bundle used to start the test server (defaults to in-built tempalte).')
@common_options
@click.pass_context
def ci_setup(ctx, log_level, ci_version, ci_type, ci_server_home, source_dir, bundle_template):
    """Download CloudBees WAR file, and setup the starter bundle"""
    if not os.path.exists(source_dir):
        sys.exit(f"Source directory '{source_dir}' does not exist")
    # parse the source directory bundle.yaml file and copy the files under the plugins and catalog keys to the target_jenkins_home_casc_startup_bundle directory
    plugin_files = []
    with open(os.path.join(source_dir, 'bundle.yaml'), 'r') as file:
        bundle_yaml = yaml.load(file)
        for key in ['plugins', 'catalog']:
            # list paths to all entries under bundle_yaml.plugins
            if key in bundle_yaml and isinstance(bundle_yaml[key], list):
                for plugin_file in bundle_yaml[key]:
                    plugin_files.append(os.path.join(source_dir, plugin_file))
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.get_war()
    jenkins_manager.create_startup_bundle(plugin_files, bundle_template)
    _update_bundle(jenkins_manager.target_jenkins_home_casc_startup_bundle)

@cli.command()
@server_options
@click.option('-s', '--source-dir', 'source_dir',  required=True, type=click.Path(file_okay=False, dir_okay=True), help='The bundle to be validated.')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help='Do not fail if warnings are found.')
@common_options
@click.pass_context
def ci_validate(ctx, log_level, ci_version, ci_type, ci_server_home, source_dir, ignore_warnings):
    """Validate bundle against controller started with ci-start-server."""
    set_logging(ctx, log_level)
    if not os.path.exists(source_dir):
        sys.exit(f"Source directory '{source_dir}' does not exist")
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    server_url, username, password = jenkins_manager.get_server_details()
    logging.debug(f"Server URL: {server_url}, Username: {username}, Password: {password}")
    _validate(server_url, username, password, source_dir, ignore_warnings)

@cli.command()
@server_options
@common_options
@click.pass_context
def ci_start(ctx, log_level, ci_version, ci_type, ci_server_home):
    """Start CloudBees Server"""
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.start_server()

@cli.command()
@server_options
@common_options
@click.pass_context
def ci_stop(ctx, log_level, ci_version, ci_type, ci_server_home):
    """Stop CloudBees Server"""
    jenkins_manager = JenkinsServerManager(ci_type, ci_version, ci_server_home)
    jenkins_manager.stop_server()

# add a diff command to diff two directories by calling the diff command on each file
@cli.command()
@click.argument('src1', type=click.Path(exists=True))
@click.argument('src2', type=click.Path(exists=True))
@common_options
@click.pass_context
def diff(ctx, log_level, src1, src2):
    """Diff two YAML directories or files."""
    set_logging(ctx, log_level)
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
        sys.exit("src1 and src2 must both be either directories or files")
    if diff_detected:
        sys.exit("Differences detected")

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

# add completion command which takes the shell as an argument
# shell can only be bash, fish, or zsh
@cli.command()
@click.option('-s', '--shell', 'shell', required=True, type=click.Choice(['bash', 'fish', 'zsh']), help='The shell to generate completion script for.')
@click.pass_context
def completion(ctx, shell):
    """Print the shell completion script"""
    ctx.ensure_object(dict)
    # run process 'echo "$(_BUNDLEUTILS_COMPLETE=bash_source bundleutils)"'
    click.echo("Run either of the following commands to enable completion:")
    click.echo(f'  1. eval "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})"')
    click.echo(f'  2. echo "$(_{script_name_upper}_COMPLETE={shell}_source {script_name})" > {script_name}-complete.{shell}')
    click.echo(f'     source {script_name}-complete.{shell}')

def null_check(obj, obj_name, obj_env_var=None):
    if not obj:
        if obj_env_var:
            obj = os.environ.get(obj_env_var, obj)
            if not obj:
                sys.exit(f'No {obj_name} option provided and no {obj_env_var} not set')
    return obj

@cli.command()
@common_options
@click.option('-U', '--url', 'url', default=default_validate_url, help='The controller URL to fetch YAML from (or use BUNDLEUTILS_JENKINS_URL).')
@click.option('-u', '--username', 'username', help='Username for basic authentication (or use BUNDLEUTILS_USERNAME).')
@click.option('-p', '--password', 'password', help='Password for basic authentication (or use BUNDLEUTILS_PASSWORD).')
@click.option('-s', '--source-dir', 'source_dir', required=True, type=click.Path(file_okay=False, dir_okay=True), help='The source directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR).')
@click.option('-w', '--ignore-warnings', default=False, is_flag=True, help='Do not fail if warnings are found.')
@click.pass_context
def validate(ctx, log_level, url, username, password, source_dir, ignore_warnings):
    """Validate bundle in source dir against URL."""
    set_logging(ctx, log_level)
    _validate(url, username, password, source_dir, ignore_warnings)

def _validate(url, username, password, source_dir, ignore_warnings):
    username = null_check(username, 'username', 'BUNDLEUTILS_USERNAME')
    password = null_check(password, 'password', 'BUNDLEUTILS_PASSWORD')
    source_dir = null_check(source_dir, 'source directory', 'BUNDLEUTILS_SOURCE_DIR')
    url = null_check(url, 'url')
    # if the url does end with /casc-bundle-mgnt/casc-bundle-validate, append it
    if not url.endswith('/casc-bundle-mgnt/casc-bundle-validate'):
        url = url + '/casc-bundle-mgnt/casc-bundle-validate'

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
        sys.exit(f'Failed to decode JSON from response: {response.text}')
    click.echo(json.dumps(response_json, indent=2))
    # Filter out non-info messages
    non_info_messages = [message for message in response_json["validation-messages"] if not message.startswith("INFO -")]
    if non_info_messages:
        # if non info messages only include warnings...
        if all("WARNING -" in message for message in non_info_messages):
            if not ignore_warnings:
                sys.exit('Validation failed with warnings')
            else:
                logging.warning('Validation failed with warnings. Ignoring due to --ignore-warnings flag')
        else:
            sys.exit('Validation failed with errors or critical messages')

def filter_plugins(data):
    """
    Filters out plugins where enabled is False or deleted is True.
    """
    filtered_plugins = []
    plugins = data.get("plugins", [])
    for plugin in plugins:
        if plugin.get("deleted", True):
            logging.debug(f"Plugins: removing deleted plugin: {plugin['shortName']}")
            filtered_plugins.append(plugin['shortName'])
        elif not plugin.get("enabled", True):
            logging.debug(f"Plugins: removing disabled plugin: {plugin['shortName']}")
            filtered_plugins.append(plugin['shortName'])
    return filtered_plugins

@cli.command()
@common_options
@click.option('-m', '--pluginJsonUrl', 'plugin_json_url', default=default_plugin_json_url, help='The URL to fetch plugins info (or use BUNDLEUTILS_JENKINS_URL).')
@click.option('-M', '--pluginJsonPath', 'plugin_json_path', default=os.environ.get('BUNDLEUTILS_PLUGINS_JSON_PATH'), help='The path to fetch JSON file from (found at /manage/pluginManager/api/json?pretty&depth=1).')
@click.option('-P', '--path', 'path', default=os.environ.get('BUNDLEUTILS_PATH'), type=click.Path(file_okay=True, dir_okay=False), help='The path to fetch YAML from (or use BUNDLEUTILS_PATH).')
@click.option('-U', '--url', 'url', default=default_fetch_url, help='The URL to fetch YAML from (or use BUNDLEUTILS_JENKINS_URL).')
@click.option('-u', '--username', 'username', default=os.environ.get('BUNDLEUTILS_USERNAME'), help='Username for basic authentication (or use BUNDLEUTILS_USERNAME).')
@click.option('-p', '--password', 'password', default=os.environ.get('BUNDLEUTILS_PASSWORD'), help='Password for basic authentication (or use BUNDLEUTILS_PASSWORD).')
@click.option('-t', '--target-dir', 'target_dir', default=os.environ.get('BUNDLEUTILS_TARGET_DIR', default_target), help='The target directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR).')
@click.pass_context
def fetch(ctx, log_level, url, path, username, password, target_dir, plugin_json_url, plugin_json_path):
    """Fetch YAML documents from a URL or path."""
    set_logging(ctx, log_level)
    # if path or url is not provided, look for a zip file in the current directory matching the pattern core-casc-export-*.zip
    if not path and not url:
        zip_files = glob.glob('core-casc-export-*.zip')
        if len(zip_files) == 1:
            logging.info(f'Found core-casc-export-*.zip file: {zip_files[0]}')
            path = zip_files[0]
        elif len(zip_files) > 1:
            sys.exit('Multiple core-casc-export-*.zip files found in the current directory')
    if not plugin_json_path and not plugin_json_url:
        plugin_json_files = glob.glob('plugins*.json')
        if len(plugin_json_files) == 1:
            logging.info(f'Found plugins*.json file: {plugin_json_files[0]}')
            plugin_json_path = plugin_json_files[0]
        elif len(plugin_json_files) > 1:
            sys.exit('Multiple plugins*.json files found in the current directory')
    try:
        fetch_yaml_docs(url, path, username, password, target_dir)
    except Exception as e:
        sys.exit(f'Failed to fetch and write YAML documents: {e}')
    try:
        update_plugins(plugin_json_url, plugin_json_path, username, password, target_dir)
    except Exception as e:
        sys.exit(f'Failed to fetch and update plugin data: {e}')


def update_plugins(plugin_json_url, plugin_json_path, username, password, target_dir):
    # if the plugin_json_url is set, fetch the plugins JSON from the URL
    if plugin_json_url:
        logging.debug(f'Loading plugin JSON from URL: {plugin_json_url}')
        response_text = call_jenkins_api(plugin_json_url, username, password)
        # parse text as JSON
        data = json.loads(response_text)
        filtered_plugins = filter_plugins(data)
        # if the plugins.yaml file exists in the target directory, remove the filtered plugins from the file
    elif plugin_json_path:
        logging.debug(f'Loading plugin JSON from path: {plugin_json_path}')
        with open(plugin_json_path, 'r') as f:
            data = json.load(f)
        filtered_plugins = filter_plugins(data)
    else:
        logging.info('No plugin JSON URL or path provided. Cannot determine if disabled/deleted plugins present in list.')
        return

    # removing from the plugins.yaml file
    plugins_file = os.path.join(target_dir, 'plugins.yaml')
    if os.path.exists(plugins_file):
        with open(plugins_file, 'r') as f:
            plugins_data = yaml.load(f)  # Load the existing data

        logging.info(f"Looking for disabled/deleted plugins to remove from plugins.yaml")
        # Check if 'plugins' key exists and it's a list
        if 'plugins' in plugins_data and isinstance(plugins_data['plugins'], list):
            updated_plugins = []
            for plugin in plugins_data['plugins']:
                if plugin['id'] in filtered_plugins:
                    logging.info(f" -> removing: {plugin['id']}")
                else:
                    updated_plugins.append(plugin)

            plugins_data['plugins'] = updated_plugins
        with open(plugins_file, 'w') as f:
            yaml.dump(plugins_data, f)  # Write the updated data back to the file

    # removing from the plugin-catalog.yaml file
    plugin_catalog = os.path.join(target_dir, 'plugin-catalog.yaml')
    if os.path.exists(plugin_catalog):
        with open(plugin_catalog, 'r') as f:
            catalog_data = yaml.load(f)  # Load the existing data

        logging.info(f"Looking for disabled/deleted plugins to remove from plugin-catalog.yaml")
        # Check and remove plugins listed in filtered_plugins from includePlugins
        for configuration in catalog_data.get('configurations', []):
            if 'includePlugins' in configuration:
                for plugin_id in list(configuration['includePlugins']):
                    if plugin_id in filtered_plugins:
                        del configuration['includePlugins'][plugin_id]
                        logging.info(f" -> removing: {plugin_id}")

        with open(plugin_catalog, 'w') as file:
            yaml.dump(catalog_data, file) # Write the updated data back to the file

def fetch_yaml_docs(url, path, username, password, target_dir):
    # place each document in a separate file under a target directory
    logging.debug(f'Creating target directory: {target_dir}')
    os.makedirs(target_dir, exist_ok=True)

    # remove any existing files
    logging.debug(f'Removing files in {target_dir}')
    for filename in os.listdir(target_dir):
        filename = os.path.join(target_dir, filename)
        os.remove(filename)

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
                            logging.debug(f'Read YAML from file: {filename}')
                            doc = yaml.load(f)
                            write_yaml_doc(doc, target_dir, filename)
                        else:
                            logging.warning(f'Skipping empty file: {filename}')
        else:
            logging.info(f'Read YAML from path: {path}')
            with open(path, 'r') as f:
                yaml_docs = list(yaml.load_all(f))
                write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    elif url:
        logging.info(f'Read YAML from url: {url}')
        response_text = call_jenkins_api(url, username, password)
        # logging.debug(f'Fetched YAML from {url}:\n{response.text}')
        yaml_docs = list(yaml.load_all(response_text))
        write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    else:
        sys.exit('No path or URL provided')

def call_jenkins_api(url, username, password):
    logging.debug(f'Fetching response from URL: {url}')
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

def normalize_yaml(data):
    """Normalize a nested dictionary."""
    if isinstance(data, dict):
        return {k: normalize_yaml(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [normalize_yaml(v) for v in data]
    elif isinstance(data, str):
        # Normalize strings that contain newline characters
        if '\\n' in data:
            return '|\n' + data.replace('\\n', '\n')
        else:
            return data
    else:
        return data

def traverse_credentials(filename, obj, custom_replacements={}, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}/{k}" if path else f"/{k}"
            if isinstance(v, str) and re.match(r'{.*}', v) and 'id' in obj:
                id = obj['id']
                # if custom replacement found for this id, use the custom replacement value
                matching_tuple = next((item for item in custom_replacements if item['id'] == id), None)
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

                # print the JSON Patch operation for the replacement
                patch = {"op": "replace", "path": f'{new_path}', "value": f'{replacement}'}
                apply_patch(filename, [patch])
                continue
            traverse_credentials(filename, v, custom_replacements, new_path)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_path = f"{path}/{i}"
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
@common_options
@transform_options
@click.pass_context
def normalize(ctx, log_level, strict, configs, source_dir, target_dir):
    """Transform using the normalize.yaml for better comparison."""
    set_logging(ctx, log_level)
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
@common_options
@transform_options
@click.pass_context
def operationalize(ctx, log_level, strict, configs, source_dir, target_dir):
    """Transform using the operationalize.yaml (run normalise first)."""
    set_logging(ctx, log_level)
    if not source_dir:
        source_dir = default_normalized
    if not target_dir:
        target_dir = default_operationalized
    if not configs:
        # if a normalize.yaml file is found in the current directory, use it
        if os.path.exists('operationalize.yaml'):
            logging.info('Using operationalize.yaml in the current directory')
            configs = ['operationalize.yaml']
        else:
            path = pkg_resources.files('defaults.configs') / 'operationalize.yaml'
            configs = [path]
    _transform(configs, source_dir, target_dir)

@cli.command()
@common_options
@transform_options
@click.pass_context
def transform(ctx, log_level, strict, configs, source_dir, target_dir):
    """Transform using a custom transformation config."""
    set_logging(ctx, log_level)
    _transform(configs, source_dir, target_dir)

@click.pass_context
def _file_check(ctx, file, strict=False):
    # if file does not exist, or is empty, skip
    logging.debug(f'Checking file: {file}')
    if not os.path.exists(file) or os.path.getsize(file) == 0:
        # if default_fail_on_missing is set, raise an exception
        if ctx.params["strict"] or strict:
            sys.exit(f'File {file} does not exist')
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
@common_options
@click.option('-t', '--target-dir', 'target_dir', required=True, type=click.Path(file_okay=False, dir_okay=True), help='The target directory to update the bundle.yaml file.')
@click.pass_context
def update_bundle(ctx, log_level, target_dir):
    """Update the bundle.yaml file in the target directory."""
    set_logging(ctx, log_level)
    _update_bundle(target_dir)

def _update_bundle(target_dir):
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

    # update the version key with the md5sum of the content of all files
    data['version'] = os.popen(f'cat {" ".join([os.path.join(target_dir, file) for file in all_files])} | md5sum').read().split()[0]

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
    logging.debug('Loading YAML object')

    full_filename = os.path.join(target_dir, filename)
    if not _file_check(full_filename):
        return
    with open(full_filename, 'r') as f:
        data = yaml.load(f)

    new_data = {}
    removed_items = []

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
