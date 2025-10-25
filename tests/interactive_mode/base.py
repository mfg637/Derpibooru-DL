import unittest
import interactive_mode


class DummyCommand(interactive_mode.Command):
    def __init__(self):
        super().__init__(
            command_name="dummy_command",
            command_aliases=["dummy"],
            command_description="This is a placeholder for unit testing",
            required_arguments={"id": interactive_mode.types.IntegerArgument()},
            optional_arguments={
                "name": interactive_mode.types.StringArgument()
            },
            args_position=["id"],
        )

    def execute(self, *required_arguments, **optional_arguments):
        self.arguments_processing(*required_arguments, **optional_arguments)


class TestArgumentsProcessing(unittest.TestCase):
    def setUp(self):
        self.command = DummyCommand()

    def test_all_arguments_provided(self):
        arguments = self.command.arguments_processing("1", name="test")
        self.assertDictEqual(arguments, {"id": 1, "name": "test"})

    def test_required_argument_provided(self):
        arguments = self.command.arguments_processing("2")
        self.assertDictEqual(arguments, {"id": 2, "name": None})

    def test_missing_required_argument(self):
        with self.assertRaises(
            interactive_mode.exceptions.MissingRequiredArgument
        ):
            self.command.arguments_processing()

    def test_wrong_required_argument(self):
        with self.assertRaises(ValueError):
            self.command.arguments_processing("test")

    def test_wrong_positional_argument(self):
        with self.assertRaises(ValueError):
            self.command.arguments_processing("3", name=True)
