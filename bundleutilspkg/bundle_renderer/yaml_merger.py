import io
import logging
from ruamel.yaml import YAML

yaml = YAML(typ="rt")

default_merge_configs = {
    "dict_custom_keys": {
        "jenkins.clouds.kubernetes": "name",
    },
    "dict_strategy_config": {
        "jenkins.primaryView": "replace",
    },
    "list_strategy_config": {
        "jenkins.clouds": "append",
        "jenkins.clouds.kubernetes[*].kubernetes.templates": "merge_key:name",
        "jenkins.globalNodeProperties": "append",
        "jenkins.globalNodeProperties.envVars.env": "merge_key:key",
        "support.automatedBundleConfiguration.componentIds": "append",
        "plugins": "merge_key:id",
        "items": "merge_key:name",
    },
    "do_not_append": {
        "jenkins.globalNodeProperties": ["envVars"],
    }
}

def printYaml(obj):
    stream = io.StringIO()
    yaml.dump(obj, stream)
    return stream.getvalue()

class YAMLMerger:
    def __init__(self, merge_configs=None):
        """
        Initializes YAML merger with configurable list merging strategies based on paths.
        """
        if merge_configs is None:
            merge_configs = default_merge_configs
        logging.info(f"Using the following merge configs:\n{printYaml(merge_configs)}")
        self.dict_strategy_config = merge_configs["dict_strategy_config"] or {}
        self.dict_custom_keys = merge_configs["dict_custom_keys"] or {}
        self.list_strategy_config = merge_configs["list_strategy_config"] or {}
        self.do_not_append = merge_configs["do_not_append"] or {}

    def _check_custom_key(self, key, path, item, do_not_append):
        """
        Checks if a custom key is defined for the given key and path.
        """
        custom_key = None
        for custom_key_pattern, custom_key_value  in self.dict_custom_keys.items():
            path_and_key = f"{path}.{key}"
            logging.debug(f"Checking custom key pattern: {custom_key_pattern} against path: {path} and key: {key}")
            count_star = custom_key_pattern.count("*")
            if count_star == 0:
                if path_and_key == custom_key_pattern:
                    custom_key = custom_key_value
            elif count_star == 1:
                start, end = custom_key_pattern.split("*")
                if path_and_key.startswith(start) and path_and_key.endswith(end):
                    custom_key = custom_key_value
            else:
                raise ValueError(f"Custom key pattern {custom_key_pattern} contains more than one '*' character {count_star}")
            if custom_key:
                logging.debug(f"Found custom key: '{custom_key}' for path: '{path}' and key: '{key}'")
                if key in do_not_append:
                    raise ValueError(f"Cannot combine do_not_append logic with custom key. Use list_strategy_config with merge_key instead.")
                if custom_key not in item[key]:
                    raise ValueError(f"Custom key: '{custom_key}' not found in dict at path: {path_and_key}")
                key = f"{key}[{item[key][custom_key]}]"
                break
        return key

    def _check_custom_strategy(self, strategy_config, path, default):
        """
        Checks if a custom key is defined for the given key and path.
        """
        custom_strategy = None
        for custom_pattern, custom_value  in strategy_config.items():
            logging.debug(f"Checking custom strategy pattern: {custom_pattern} against path: {path} and default: {default}")
            count_star = custom_pattern.count("*")
            if count_star == 0:
                if path == custom_pattern:
                    custom_strategy = custom_value
            elif count_star == 1:
                start, end = custom_pattern.split("*")
                if path.startswith(start) and path.endswith(end):
                    custom_strategy = custom_value
            else:
                raise ValueError(f"Custom key pattern {custom_pattern} contains more than one '*' character {count_star}")
            if custom_strategy:
                logging.debug(f"Found custom strategy: '{custom_strategy}' for path: '{path}'")
                break
        return custom_strategy if custom_strategy else default

    def _merge_dict_lists(self, list1, list2, path):
        """Merges lists of dictionaries, preserving unique non-dict values while respecting exclusions."""
        merged_dicts = {}
        merged_list = []

        do_not_append = self.do_not_append.get(path, [])

        # Process existing dictionaries by key
        for item in list1:
            if isinstance(item, dict):
                key = next(iter(item.keys()), None)
                if key:
                    key = self._check_custom_key(key, path, item, do_not_append)
                    logging.info(f"Adding dict path: {path}.{key}")
                    merged_dicts[key] = item  # Preserve allowed dictionary keys
            else:
                logging.info(f"Adding non-dict value path: {path} ({item})")
                merged_list.append(item)  # Keep non-dict values

        # Merge dictionaries from list2
        for item in list2:
            if isinstance(item, dict):
                key = next(iter(item.keys()), None)
                if not key:
                    continue
                key = self._check_custom_key(key, path, item, do_not_append)
                merge_path = path if key in do_not_append else f"{path}.{key}"
                if key in merged_dicts:
                    logging.debug(f"List 2 - Merging dict path: {merge_path}")
                    merged_dicts[key] = self.deep_merge(merged_dicts[key], item, merge_path)
                else:
                    logging.debug(f"List 2 - Adding dict path: {merge_path}")
                    merged_dicts[key] = item
            else:
                if item not in merged_list:
                    logging.debug(f"List 2 - Adding non-dict value path: {path} ({item})")
                    merged_list.append(item)  # Avoid duplicates for non-dict values

        return merged_list + list(merged_dicts.values())

    def deep_merge(self, parent, child, path=""):
        """Recursively merges child into parent, handling lists based on specified strategies and exclusions."""
        logging.info(f"Deep merging path: {path}")
        if isinstance(parent, dict) and isinstance(child, dict):
            for key, value in child.items():
                new_path = f"{path}.{key}" if path else key
                strategy = self._check_custom_strategy(self.dict_strategy_config, path, "merge")
                logging.debug(f"Handling dict at path: {new_path} with strategy: {strategy}")
                if key not in parent or strategy == "replace":
                    logging.debug(f"Adding dict at path: {new_path} with key: {key}")
                    parent[key] = value
                else:
                    logging.debug(f"Merging path: {new_path} with key: {key}")
                    parent[key] = self.deep_merge(parent[key], value, new_path)
        elif isinstance(parent, list) and isinstance(child, list):
            strategy = self._check_custom_strategy(self.list_strategy_config, path, "replace")
            # strategy = self.list_strategy_config.get(path, "replace")
            logging.debug(f"Handling list at path: {path} with strategy: {strategy}")
            if strategy == "append":
                return self._merge_dict_lists(parent, child, path)
            elif strategy.startswith("merge_key:"):
                key = strategy.split(":")[1]
                merged = {item[key]: item for item in parent if isinstance(item, dict) and key in item}

                for item in child:
                    if isinstance(item, dict) and key in item:
                        merged[item[key]] = self.deep_merge(merged.get(item[key], {}), item, f"{path}[{item[key]}]")
                    else:
                        if item not in parent:
                            parent.append(item)

                return list(merged.values())
            elif strategy == "replace":
                return child
            else:
                raise ValueError(f"Unknown list strategy: {strategy}")
        elif isinstance(parent, dict) and isinstance(child, list):
            raise ValueError(f"Cannot merge list into dict at path: {path}")
        elif isinstance(parent, list) and isinstance(child, dict):
            raise ValueError(f"Cannot merge dict into list at path: {path}")
        else:
            logging.debug(f"Overwriting primitive at path: {path}")
            return child  # Overwrite primitive types

        return parent

    def merge_yaml_files(self, files):
        # merge the files sequentially using the last result as the base
        output = {}
        parent = files[0]
        if len(files) < 2:
            output = self.merge_yaml_individual_files(parent, None)
        else:
            parent_object = None
            for file in files[1:]:
                output = self.merge_yaml_individual_files(parent, file, parent_object)
                parent_object = output
                parent = None
        return output


    def merge_yaml_individual_files(self, parent_file, child_file, parent_object=None):
        """Loads, merges, and returns merged YAML data while considering exclusion rules."""
        logging.info(f"Merging parent file: {parent_file} with child file: {child_file}")
        if parent_object:
            parent_data = parent_object
        else:
            with open(parent_file, "r") as f:
                parent_data = yaml.load(f)

        if not child_file:
            logging.info("No child file provided, returning parent data.")
            return parent_data

        with open(child_file, "r") as f:
            child_data = yaml.load(f)

        return self.deep_merge(parent_data, child_data)
