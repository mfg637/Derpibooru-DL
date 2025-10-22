import abc
import typing
import collections.abc
from . import types


class Command(abc.ABC):
    def __init__(
        self,
        command_name: str,
        command_aliases: list[str],
        command_description: str,
        required_arguments: dict[str, types.ArgumentType],
        optional_arguments: dict[str, types.ArgumentType],
        args_position: list[str],
    ):
        self.name = command_name
        self.aliases = command_aliases
        self.description = command_description
        self.required_arguments: dict[str, types.ArgumentType] = (
            required_arguments
        )
        self.optional_arguments: dict[str, types.ArgumentType] = (
            optional_arguments
        )
        argument_names_awaiting = set(
            [argument_name for argument_name in self.required_arguments]
        )
        self.args_position: list[str] = []
        for argument_name in args_position:
            if argument_name in argument_names_awaiting:
                self.args_position.append(argument_name)
                argument_names_awaiting.remove(argument_name)
            else:
                raise ValueError(
                    f"Not found argument with name {argument_name}"
                )
        if argument_names_awaiting:
            raise ValueError("There is argument names without argument types.")

    @abc.abstractmethod
    def execute(self, *required_arguments, **positional_arguments):
        pass

    def arguments_processing(
        self, *required_arguments, **optional_arguments: str
    ) -> dict[str, typing.Any]:
        if len(required_arguments) != len(self.args_position):
            raise Exception(
                (
                    f"Command {self.name} "
                    f"expects {len(self.args_position)} "
                    "required arguments"
                )
            )
        arguments = {
            argument_name: None for argument_name in self.optional_arguments
        }
        for index, argument_name in enumerate(self.args_position):
            argument_type = self.required_arguments[argument_name]
            arguments[argument_name] = argument_type.parse_input(
                required_arguments[index]
            )
        for argument_name in optional_arguments:
            argument_type = self.optional_arguments[argument_name]
            arguments[argument_name] = argument_type.parse_input(
                optional_arguments[argument_name]
            )
        return arguments


class QuitCommand(Command):
    def __init__(self, quit_callback: collections.abc.Callable):
        super().__init__("quit", ["q", "exit"], "Exit from program", {}, {}, [])
        self.quit_callback = quit_callback

    def execute(self, *required_arguments, **positional_arguments):
        self.quit_callback()


class ShowHelpCommand(Command):
    def __init__(self):
        super().__init__(
            "help",
            [
                "h",
            ],
            "Show help mesage",
            {},
            {"command_name": types.StringArgument()},
            [],
        )
        self.commands_list: list[Command] | None = None

    def set_commands_list(self, commands_list: list[Command]):
        if type(commands_list) is list and commands_list:
            self.commands_list = commands_list
        else:
            if type(commands_list) is not list:
                raise TypeError("List type expected for commands list")
            elif not commands_list:
                raise ValueError("List of commands expected to be not empty")

    def show_commands_list(self):
        if self.commands_list is None:
            raise ValueError("Commands list were not initialized")
        print("List of available commands:")
        for command in self.commands_list:
            print(f"{command.name}: {command.description}")

    def show_command_help(self, command_name: str):
        if self.commands_list is None:
            raise ValueError("Commands list were not initialized")
        command_object: Command | None = None
        for command in self.commands_list:
            if command.name == command_name:
                command_object = command
                break
        if command_object is None:
            raise ValueError(f"Command with name {command_name} not found")
        if command_object.aliases:
            aliases_str = ", ".join(command_object.aliases)
            print(
                (
                    f"{command_object.name} (aliases: {aliases_str}): "
                    f"{command_object.description}"
                )
            )
        else:
            print(f"{command_object.name}: {command_object.description}")
        required_arguments_str: list[str] = []
        optional_arguments_str: list[str] = []
        for argument_name in command_object.args_position:
            argument_type: types.ArgumentType | None = (
                command_object.required_arguments.get(argument_name, None)
            )
            if argument_type is None:
                raise Exception(f"Argument not found: {argument_name}")
            required_arguments_str.append(f"{argument_name}:{argument_type}")
        for (
            argument_name,
            argument_type,
        ) in command_object.optional_arguments.items():
            optional_arguments_str.append(f"{argument_name}:{argument_type}")
        argument_string: str | None = None
        if required_arguments_str and optional_arguments_str:
            requires_argument_string = ", ".join(required_arguments_str)
            optional_argument_string = ", ".join(optional_arguments_str)
            argument_string = (
                f"\t{requires_argument_string} [{optional_argument_string}]"
            )
        elif required_arguments_str:
            requires_argument_string = ", ".join(required_arguments_str)
            argument_string = f"\t{requires_argument_string}"
        elif optional_arguments_str:
            optional_argument_string = ", ".join(optional_arguments_str)
            argument_string = f"\t[{optional_argument_string}]"
        if argument_string is not None:
            print(argument_string)
        else:
            print("\t[]")

    def execute(self, *required_arguments, **optional_arguments):
        arguments = self.arguments_processing(
            *required_arguments, **optional_arguments
        )
        command_name = arguments.get("command_name", None)
        if command_name is not None:
            self.show_command_help(command_name)
        else:
            self.show_commands_list()


class InteractiveEnvironment:
    def __init__(self, prompt: str = "> "):
        self.commands_list: list[Command] = []
        self.awaiting_commands: bool = False
        self.prompt = prompt

    def quit_callback(self):
        self.awaiting_commands = False

    def add_command(self, command: Command):
        self.commands_list.append(command)

    @staticmethod
    def parse_command(user_input: str):
        command_arguments = user_input.split(" ")
        command_name: str | None = None
        required_arguments: list[str] = []
        optional_arguments: dict[str, str] = {}
        for i, argument in enumerate(command_arguments):
            if i == 0:
                command_name = argument
            else:
                if (
                    "=" in argument
                    and types.url_regex.fullmatch(argument) is None
                ):
                    argument_name, argument_value = argument.split(
                        "=", maxsplit=1
                    )
                    optional_arguments[argument_name] = argument_value
                else:
                    required_arguments.append(argument)
        if command_name is None:
            raise ValueError("Command name is missing")
        return command_name, required_arguments, optional_arguments

    @staticmethod
    def get_command_by_name_or_alias(
        commands_list: list[Command],
    ) -> dict[str, Command]:
        result: dict[str, Command] = {}

        for command in commands_list:
            result[command.name] = command
            for alias in command.aliases:
                result[alias] = command
        return result

    def start(self):
        commands_list = self.commands_list.copy()
        commands_list.append(QuitCommand(self.quit_callback))
        help_command = ShowHelpCommand()
        commands_list.append(help_command)
        help_command.set_commands_list(commands_list)

        command_by_name_or_alias: dict[str, Command] = (
            self.get_command_by_name_or_alias(commands_list)
        )

        self.awaiting_commands = True
        print(
            (
                'Type "help" for list of commands '
                'or "help command_name=help" for details'
            )
        )
        while self.awaiting_commands:
            user_input = input(self.prompt)
            command_name, required_arguments, optional_arguments = (
                self.parse_command(user_input)
            )
            command = command_by_name_or_alias[command_name]
            try:
                command.execute(*required_arguments, **optional_arguments)
            except ValueError as e:
                print("Error:", e)
