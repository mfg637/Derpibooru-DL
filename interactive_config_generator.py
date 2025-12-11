import os
import json
import typing
import pathlib
import interactive_mode
import re
from interactive_mode import types
from config import definitions
from dotenv import load_dotenv

environment_variables_used: bool = False


T = typing.TypeVar("T", covariant=False)


load_dotenv()
im = interactive_mode.InteractiveEnvironment()
app_dir = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
config_file_json = app_dir.joinpath("config.json")


class ConfigEntry[T](interactive_mode.types.MutableUserDefined):
    def __init__(
        self,
        name: str,
        _type: types.ArgumentType,
        required: bool,
        name_in_config: str | None = None,
    ):
        self.name: str = name
        if name_in_config is None:
            self.name_in_config = name
        else:
            self.name_in_config = name_in_config
        self.type: types.ArgumentType = _type
        self.required: bool = required
        self.value: T | None = self.set_default_value()
        self.write_required: bool = False

    def set_default_value(self) -> T | None:
        return None

    def set_value(self, value: T | str):
        if isinstance(value, str):
            self.value = self.type.parse_input(value)
        elif value is not None:
            self.value = value
        else:
            raise TypeError(f"Expected type {self.type} or string")
        self.write_required = True

    def get_value(self) -> T:
        if self.value is not None:
            return self.value
        else:
            raise ValueError("Value is not set")

    def read_value_from_input(self, prompt: str | None = None):
        if prompt is None:
            raw_value = self.type.input(f"{self.name}: ")
        else:
            raw_value = self.type.input(prompt)
        self.set_value(raw_value)

    def is_valid(self) -> bool:
        if self.required:
            return self.value is not None
        else:
            return True

    def is_empty(self) -> bool:
        return self.value is None

    def __str__(self):
        is_valid = "" if self.is_valid() else "*"
        type_hint = self.type.type_label
        if not self.required:
            type_hint = f"{self.type.type_label} | None"
        return f"{is_valid}{self.name}: {type_hint} = {self.value}"


class ConfigEntriesGroup(interactive_mode.types.MutableUserDefined):
    def __init__(self, name: str):
        self.name: str = name
        self.entries: dict[str, ConfigEntry] = {}

    def add_entry(self, entry: ConfigEntry):
        self.entries[entry.name] = entry

    def check_is_valid(self) -> bool:
        for entry_name in self.entries:
            if not self.entries[entry_name].is_valid():
                return False
        return True

    def get_entry(self, entry_name) -> ConfigEntry:
        entry = self.entries.get(entry_name, None)
        if entry is None:
            raise ValueError(f"Entry with name {entry_name} not found")
        return entry

    def get_entries_by_config_name(self) -> dict[str, ConfigEntry]:
        result = {}
        for entry in self.entries.values():
            result[entry.name_in_config] = entry
        return result

    def __str__(self):
        is_valid = "" if self.check_is_valid() else "*"
        return f"{is_valid}{self.name} ({len(self.entries)} entries)"

    def __repr__(self):
        repr_string = f"{self.name}:"
        for entry_name in self.entries:
            repr_string += f"\n\t{self.entries[entry_name]}"
        return repr_string


class ConfigManager:
    def __init__(self):
        self.entry_groups: dict[str, ConfigEntriesGroup] = {}

    def check_is_valid(self) -> bool:
        for group_name in self.entry_groups:
            if not self.entry_groups[group_name].check_is_valid():
                return False
        return True

    def get_group(self, group_name) -> ConfigEntriesGroup:
        group = self.entry_groups.get(group_name, None)
        if group is None:
            raise ValueError(f"Group with name {group_name} not found")
        return group

    def show_groups_list(self):
        for group_name in self.entry_groups:
            print(str(self.entry_groups[group_name]))

    def add_group(self, group: ConfigEntriesGroup):
        self.entry_groups[group.name] = group


server_settings = ConfigEntriesGroup("server_settings")
server_settings.add_entry(
    ConfigEntry[str]("host", types.StringArgument(), False)
)
server_settings.add_entry(
    ConfigEntry[str]("webhost", types.StringArgument(), False)
)
server_settings.add_entry(
    ConfigEntry[int]("port", types.IntegerArgument(), False)
)
server_settings.add_entry(
    ConfigEntry[bool](
        "manual_start", types.BooleanType(), False, "manual start"
    )
)


class InitialDirectoryConfigEntry(ConfigEntry[pathlib.Path]):
    def __init__(self):
        super().__init__(
            "initial_dir", types.ExistingFilePath(), True, "initial dir"
        )

    def set_default_value(self):
        pathstr = os.getenv("DDL_initial_dir", None)
        if pathstr is None:
            return None
        else:
            return pathlib.Path(pathstr)


filesystem_settings = ConfigEntriesGroup("filesystem_settings")
filesystem_settings.add_entry(InitialDirectoryConfigEntry())
filesystem_settings.add_entry(
    ConfigEntry[str](
        "saving_path",
        types.StringEnumType(definitions.PathSpecification),
        False,
        "saving path",
    )
)
filesystem_settings.add_entry(
    ConfigEntry[bool](
        "use_api_name", types.BooleanType(), False, "use API provided name"
    )
)
filesystem_settings.add_entry(
    ConfigEntry[int](
        "max_name_length",
        types.IntegerArgument(),
        False,
        "max API provided name length",
    )
)


class OptionalEnvStringConfigEntry(ConfigEntry[str]):
    def __init__(self, name: str, name_in_config: str, env_name: str):
        self.env_name = env_name
        super().__init__(name, types.StringArgument(), False, name_in_config)

    def set_default_value(self):
        return os.getenv(self.env_name, None)


class RequiredEnvStringConfigEntry(ConfigEntry[str]):
    def __init__(self, name: str, name_in_config: str, env_name: str):
        self.env_name = env_name
        super().__init__(name, types.StringArgument(), True, name_in_config)

    def set_default_value(self):
        return os.getenv(self.env_name, None)


class OptionalEnvPasswordConfigEntry(ConfigEntry[str]):
    def __init__(self, name: str, name_in_config: str, env_name: str):
        self.env_name = env_name
        super().__init__(
            name,
            types.PasswordArgument(double_check=True),
            False,
            name_in_config,
        )

    def __str__(self):
        type_hint = f"{self.type.type_label} | None"
        if self.value is None:
            value = None
        else:
            value = re.sub(r".", "*", self.value)
        return f"{self.name}: {type_hint} = {value}"


class RequiredEnvPasswordConfigEntry(ConfigEntry[str]):
    def __init__(self, name: str, name_in_config: str, env_name: str):
        self.env_name = env_name
        super().__init__(
            name,
            types.PasswordArgument(double_check=True),
            True,
            name_in_config,
        )

    def __str__(self):
        is_valid = "" if self.is_valid() else "*"
        type_hint = self.type.type_label
        if self.value is None:
            value = None
        else:
            value = re.sub(r".", "*", self.value)
        return f"{is_valid}{self.name}: {type_hint} = {value}"


api_keys = ConfigEntriesGroup("api_keys")
api_keys.add_entry(
    OptionalEnvPasswordConfigEntry(
        "derpibooru_key", "derpibooru API key", "DERPIBOORU_API_KEY"
    )
)
api_keys.add_entry(
    OptionalEnvPasswordConfigEntry(
        "twibooru_key", "twibooru API key", "TWIBOORU_API_KEY"
    )
)
api_keys.add_entry(
    OptionalEnvPasswordConfigEntry(
        "ponybooru_key", "ponybooru API key", "PONYBOORU_API_KEY"
    )
)
api_keys.add_entry(
    OptionalEnvStringConfigEntry("e621_login", "e621 login", "E621_LOGIN")
)
api_keys.add_entry(
    OptionalEnvPasswordConfigEntry("e621_key", "e621 API key", "E621_API_KEY")
)


ui_settings = ConfigEntriesGroup("ui_settings")
ui_settings.add_entry(
    ConfigEntry[bool]("enable_gui", types.BooleanType(), False, "enable gui")
)


database_settings = ConfigEntriesGroup("database_settings")
database_settings.add_entry(
    RequiredEnvStringConfigEntry(
        "app_user", "Application database user", "DDL_DB_USER"
    )
)
database_settings.add_entry(
    RequiredEnvPasswordConfigEntry(
        "app_password", "Application database password", "DDL_DB_PASSWORD"
    )
)
database_settings.add_entry(
    RequiredEnvStringConfigEntry(
        "app_host", "Application database hostname", "DDL_DB_HOST"
    )
)
database_settings.add_entry(
    RequiredEnvStringConfigEntry(
        "prod_db_name", "Production database name", "DDL_DB_PROD"
    )
)
database_settings.add_entry(
    RequiredEnvStringConfigEntry(
        "test_db_name", "Testing database name", "DDL_DB_TEST"
    )
)
database_settings.add_entry(
    OptionalEnvStringConfigEntry(
        "derpi_db_hostname",
        "Derpibooru database dump hostname",
        "DERPIBOORU_DUMP_HOST",
    )
)
database_settings.add_entry(
    OptionalEnvStringConfigEntry(
        "derpi_db_user",
        "Derpibooru database dump username",
        "DERPIBOORU_DUMP_USER",
    )
)
database_settings.add_entry(
    OptionalEnvPasswordConfigEntry(
        "derpi_db_password",
        "password for derpibooru database dump",
        "DERPIBOORU_DUMP_PASSWORD",
    )
)


cm = ConfigManager()
cm.add_group(server_settings)
cm.add_group(filesystem_settings)
cm.add_group(api_keys)
cm.add_group(ui_settings)
cm.add_group(database_settings)


class ShowGroupsCommand(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            "groups",
            ["group"],
            "Show list of groups or group details",
            {},
            {"group_name": types.StringArgument()},
            [],
        )

    def show_list_of_groups(self):
        cm.show_groups_list()

    def show_group_information(self, group: str | ConfigEntriesGroup):
        if isinstance(group, ConfigEntriesGroup):
            print(group.__repr__())
        else:
            group_object = cm.get_group(group)
            print(group_object.__repr__())

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        group_name: str | None = arguments.get("group_name", None)
        if group_name is None:
            if isinstance(im.context, ConfigEntriesGroup):
                self.show_group_information(im.context)
            else:
                self.show_list_of_groups()
        else:
            self.show_group_information(group_name)


class SetCurrentGroup(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            "set_group",
            [],
            "Set context pointer to specified group by name",
            {"group_name": types.StringArgument()},
            {},
            ["group_name"],
        )

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        group_name = arguments["group_name"]
        group = cm.get_group(group_name)
        im.context = group


class ClearContext(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            "clear_context", ["clear"], "Clear the context pointer", {}, {}, []
        )

    def execute(self, *required_arguments, **optional_arguments):
        im.clear_context()


ConfigValueT = typing.TypeVar("ConfigValueT", covariant=False)


class OptionNameType(types.ArgumentType[ConfigEntry[ConfigValueT]]):
    def __init__(self):
        super().__init__("option_name")

    def parse_input(self, raw_value: str) -> ConfigEntry[ConfigValueT]:
        if "." in raw_value:
            group_name, entry_name = raw_value.split(".", 1)
            group_entry = cm.get_group(group_name)
            return group_entry.get_entry(entry_name)
        else:
            if isinstance(im.context, ConfigEntriesGroup):
                group_entry = im.context
                return group_entry.get_entry(raw_value)
            else:
                raise ValueError("Config Entry not found")


class SetOption(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            "set_option",
            [],
            (
                "Set option by group_name.option_name, "
                "or just by option_name if group "
                "defined by context"
            ),
            {"option_name": OptionNameType()},
            {},
            ["option_name"],
        )

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        option_entry: ConfigEntry = arguments["option_name"]
        option_entry.read_value_from_input()


class SaveConfig(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            "save_config",
            ["save", "write", "w"],
            "Save to config.json",
            {},
            {"write_defaults": types.BooleanType()},
            [],
        )

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        write_defaults: bool | None = arguments.get("write_defaults", False)
        serialisable_config = {}
        for group_name in cm.entry_groups:
            group = cm.entry_groups[group_name]
            for entry_name in group.entries:
                entry = group.entries[entry_name]
                if entry.value is not None and (
                    entry.write_required or write_defaults
                ):
                    value = entry.value
                    if isinstance(value, pathlib.Path):
                        value = str(value)
                    serialisable_config[entry.name_in_config] = value

        if serialisable_config:
            try:
                # avoid writing corrupted config
                commit = json.dumps(serialisable_config)
                with config_file_json.open("w") as f:
                    f.write(commit)
            except Exception as e:
                raise e
            else:
                print("Sucessfully written config.json")
        else:
            print("Nothing to save")


def load_config() -> None:
    config_data = {}
    app_dir = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    config_file_json = app_dir.joinpath("config.json")
    if config_file_json.is_file():
        with config_file_json.open("r") as f:
            config_data = json.load(f)
    config_file_keys = set(config_data)
    for group_name in cm.entry_groups:
        group = cm.entry_groups[group_name]
        group_entries = group.get_entries_by_config_name()
        group_entry_names = set(group_entries)
        entry_match_found = group_entry_names & config_file_keys
        for entry_name in entry_match_found:
            group_entries[entry_name].set_value(config_data[entry_name])


load_config()


im.add_command(ShowGroupsCommand())
im.add_command(SetCurrentGroup())
im.add_command(ClearContext())
im.add_command(SetOption())
im.add_command(SaveConfig())
im.start()
