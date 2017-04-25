from ..command import command
from ..const import DEFAULT_COMMANDS_MODULE
from ..run import run
from ..runner import CommandRunner


@command
def complete(config, module=DEFAULT_COMMANDS_MODULE, words=(), index=0):
    debug = config.run.debug
    runner = CommandRunner(module, debug=debug)
    commands = runner.commands

    words = [word[1:-1] for word in words]  # Strip quotes
    current_word = words[index]
    previous_word = words[index - 1] if index > 0 else None

    def find_command():
        for word in reversed(words[:index]):
            if word in commands:
                return commands[word]
        return run

    def print_commands():
        print(' '.join(commands))

    def print_command_options(command):
        options = [option for option in command.arg_map if option.startswith('--')]
        print(' '.join(options))

    found_command = find_command()

    if current_word.startswith('-'):
        print_command_options(found_command)
    else:
        is_command_arg = previous_word in found_command.arg_map
        command_arg = found_command.arg_map[previous_word] if is_command_arg else None
        if is_command_arg and command_arg.takes_value:
            # Don't print any candidates; this will cause the shell
            # to display defaults (file names, etc).
            pass
        else:
            print_command_options(found_command)
            print_commands()
