import ast
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
import importlib.resources as pkg_resources
from deepdiff import DeepDiff
from deepdiff.helper import CannotCompare
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.comments import CommentedSeq

locale.setlocale(locale.LC_ALL, "C")

yaml = YAML(typ='rt')

script_name = os.path.basename(__file__).replace('.py', '')
script_name_upper = script_name.upper()

default_target = 'target/docs'
default_normalized = default_target + '-normalized'
default_operationalized = default_target + '-operationalized'

def common_options(func):
    func = click.option('-l', '--log-level', default=os.environ.get('BUNDLEUTILS_LOG_LEVEL', ''), help='The log level (or use BUNDLEUTILS_LOG_LEVEL).')(func)
    return func

def transform_options(func):
    func = click.option('-c', '--config', 'configs', multiple=True, default=os.environ.get('BUNDLEUTILS_TRANSFORMATIONS'), help='The transformation config(s) (or use BUNDLEUTILS_TRANSFORMATION).')(func)
    func = click.option('-s', '--source-dir', 'source_dir', default=os.environ.get('BUNDLEUTILS_SOURCE_DIR', ''), help='The source directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR).')(func)
    func = click.option('-t', '--target-dir', 'target_dir', default=os.environ.get('BUNDLEUTILS_TARGET_DIR', ''), help='The target directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR). Defaults to the source directory suffixed with -transformed.')(func)
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

# add a diff command to diff two directories by calling the diff command on each file
@cli.command()
@common_options
@click.option('-1', '--src1', 'src1', type=click.Path(exists=True))
@click.option('-2', '--src2', 'src2', type=click.Path(exists=True))
@click.pass_context
def diff(ctx, log_level, src1, src2):
    """Diff two YAML directories or files."""
    set_logging(ctx, log_level)
    # if src1 is a directory, ensure src2 is also directory
    if os.path.isdir(src1) and os.path.isdir(src2):
        files1 = os.listdir(src1)
        files2 = os.listdir(src2)
        for file1 in files1:
            if file1 in files2:
                file1_path = os.path.join(src1, file1)
                file2_path = os.path.join(src2, file1)
                # Compare the two files
                logging.info(f"Comparing {file1} in {src1} and {src2}")
                diff2(file1_path, file2_path)
            else:
                logging.warning(f"File {file1} does not exist in {src2}")
        for file2 in files2:
            if file2 not in files1:
                logging.warning(f"File {file2} does not exist in {src1}")
    elif os.path.isfile(src1) and os.path.isfile(src2):
        # Compare the two files
        logging.info(f"Comparing {src1} and {src2}")
        diff2(src1, src2)
    else:
        raise ValueError("src1 and src2 must both be either directories or files")

def diff2(file1, file2):
    dict1 = yaml2dict(file1)
    dict2 = yaml2dict(file2)
    diff = DeepDiff(dict1, dict2, ignore_order=True)
    click.echo(json.dumps(diff, indent=2))

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

@cli.command()
@common_options
@click.option('-P', '--path', 'path', default=os.environ.get('BUNDLEUTILS_PATH'), help='The path to fetch YAML from (or use BUNDLEUTILS_PATH).')
@click.option('-U', '--url', 'url', default=os.environ.get('BUNDLEUTILS_URL'), help='The controller URL to fetch YAML from (or use BUNDLEUTILS_URL).')
@click.option('-u', '--username', 'username', default=os.environ.get('BUNDLEUTILS_USERNAME'), help='Username for basic authentication (or use BUNDLEUTILS_USERNAME).')
@click.option('-p', '--password', 'password', default=os.environ.get('BUNDLEUTILS_PASSWORD'), help='Password for basic authentication (or use BUNDLEUTILS_PASSWORD).')
@click.option('-t', '--target-dir', 'target_dir', default=os.environ.get('BUNDLEUTILS_TARGET_DIR', default_target), help='The target directory for the YAML documents (or use BUNDLEUTILS_TARGET_DIR).')
@click.pass_context
def fetch(ctx, log_level, url, path, username, password, target_dir):
    """Fetch YAML documents from a URL or path."""
    set_logging(ctx, log_level)
    # if path or url is not provided, look for a zip file in the current directory matching the pattern core-casc-export-*.zip
    if not path and not url:
        zip_files = glob.glob('core-casc-export-*.zip')
        if len(zip_files) == 1:
            logging.info(f'Found core-casc-export-*.zip file: {zip_files[0]}')
            path = zip_files[0]
        elif len(zip_files) > 1:
            raise ValueError('Multiple core-casc-export-*.zip files found in the current directory')
    try:
        fetch_yaml_docs(url, path, username, password, target_dir)
    except Exception as e:
        logging.error(f'Failed to fetch and write YAML documents: {e}')

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
            logging.debug(f'Extracting YAML from ZIP file: {path}')
            with zipfile.ZipFile(path, 'r') as zip_ref:
                # list the files in the zip file
                for filename in zip_ref.namelist():
                    # read the YAML from the file
                    with zip_ref.open(filename) as f:
                        doc = yaml.load(f)
                        write_yaml_doc(doc, target_dir, filename)
        else:
            logging.debug(f'Read YAML from path: {path}')
            with open(path, 'r') as f:
                yaml_docs = list(yaml.load_all(f))
                write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    elif url:
        # fetch the YAML from the URL
        headers = {}
        if username and password:
            headers['Authorization'] = 'Basic ' + base64.b64encode(f'{username}:{password}'.encode('utf-8')).decode('utf-8')
        response = requests.get(url, headers=headers)
        # logging.debug(f'Fetched YAML from {url}:\n{response.text}')
        yaml_docs = list(yaml.load_all(response.text))
        write_all_yaml_docs_from_comments(yaml_docs, target_dir)
    else:
        raise Exception('No path or URL provided')

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
            logging.info(f'Applying JSON patch to {filename}')
            logging.debug(f' ->' + str(patch))
            obj = patch.apply(obj)
        except jsonpatch.JsonPatchConflict:
            logging.error('Failed to apply JSON patch')
            return

    # save the patched object back to the file
    with open(filename, 'w') as out:
        yaml.dump(obj, out)

def handle_patches(patches, target_dir):
    # for each key in the patches, open the file and apply the patch
    for filename, patch in patches.items():
        filename = os.path.join(target_dir, filename)
        logging.info(f'Applying patch to {filename}')
        apply_patch(filename, patch)

def apply_replacements(filename, custom_replacements):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)
        if obj is None:
            logging.error(f'Failed to load YAML object from file {filename}')
            return
        traverse_credentials(filename, obj, custom_replacements)

def apply_split(filename, split):
    with open(filename, 'r') as inp:
        obj = yaml.load(inp)
        if obj is None:
            logging.error(f'Failed to load YAML object from file {filename}')
            return

def handle_credentials(credentials, target_dir):
    # for each key in the patches, open the file and apply the patch
    for filename, replacements in credentials.items():
        filename = os.path.join(target_dir, filename)
        logging.info(f'Applying cred replacements to {filename}')
        apply_replacements(filename, replacements)

def handle_splits(splits, target_dir):
    # for type in items, jcasc, if the key exists, process
    for split_type, split_dict in splits.items():
        if split_type == 'items':
            for filename, configs in split_dict.items():
                logging.info(f'Applying split to {target_dir}/{filename}')
                logging.debug(f'Using configs: {configs}')
                split_items(target_dir, filename, configs)
        elif split_type == 'jcasc':
            for filename, configs in split_dict.items():
                logging.info(f'Applying split to {target_dir}/{filename}')
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
def normalize(ctx, log_level, configs, source_dir, target_dir):
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
            path = pkg_resources.files('bundleutilspkg.configs') / 'normalize.yaml'
            configs = [path]
    _transform(configs, source_dir, target_dir)

@cli.command()
@common_options
@transform_options
@click.pass_context
def operationalize(ctx, log_level, configs, source_dir, target_dir):
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
            path = pkg_resources.files('bundleutilspkg.configs') / 'operationalize.yaml'
            configs = [path]
    _transform(configs, source_dir, target_dir)

@cli.command()
@common_options
@transform_options
@click.pass_context
def transform(ctx, log_level, configs, source_dir, target_dir):
    """Transform using a custom transformation config."""
    set_logging(ctx, log_level)
    _transform(configs, source_dir, target_dir)


def _transform(configs, source_dir, target_dir):
    """Transform using a custom transformation config."""
    # add the transformation configs recursively into the merged config
    merged_config = {}
    for config in configs:
        with open(config, 'r') as inp:
            logging.info(f'Processing config: {config}')
            obj = yaml.load(inp)
            merged_config = recursive_merge(merged_config, obj)

    logging.debug(f'Merged config:\n' + printYaml(merged_config))
    # if the target directory is not set, use the source directory suffixed with -transformed
    if not target_dir:
        target_dir = source_dir + '-transformed'
    logging.info(f'Transforming {source_dir} to {target_dir}')
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
    handle_splits(merged_config.get('splits', {}), target_dir)
    update_bundle(target_dir)

def update_bundle(target_dir):
    keys = ['jcasc', 'items', 'plugins', 'rbac']

    # Load the YAML file
    with open(os.path.join(target_dir, 'bundle.yaml'), 'r') as file:
        data = yaml.load(file)

    all_files = []
    # Iterate over the keys
    for key in keys:
        # Special case for 'jcasc'
        if key == 'jcasc':
            prefix = 'jenkins'
        else:
            prefix = key

        # Get the list of YAML files starting with the prefix
        files = glob.glob(os.path.join(target_dir, f'{prefix}.*.yaml'))

        # Remove the target_dir path and sort the files, ensuring exact match come first
        files = sorted([os.path.basename(file) for file in files])

        # if file matches f'{prefix}.yaml', then add it to the front of the list
        exact_match = os.path.join(target_dir, f'{prefix}.yaml')
        if os.path.exists(exact_match):
            files.insert(0, f'{prefix}.yaml')

        # if no files found, remove the key from the data if it exists
        if not files:
            if key in data:
                del data[key]
            continue

        # Update the key in the data
        data[key] = files

        # Add the files to the all_files list
        all_files.extend(files)

    # update the version key with the md5sum of the content of all files
    data['version'] = os.popen(f'cat {" ".join([os.path.join(target_dir, file) for file in all_files])} | md5sum').read().split()[0]

    # Save the YAML file
    logging.info(f'Writing bundle to {target_dir}/bundle.yaml')
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
    logging.info('Loading YAML object')

    full_filename = os.path.join(target_dir, filename)
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
                    if target_file not in new_data:
                        new_data[target_file] = []
                    new_data[target_file].append(item)
                    logging.info(f' - > moving {item_name} to {target_file}')
                    removed_items.append(item)

    # Remove the items that were moved
    for item in removed_items:
        items.remove(item)
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
