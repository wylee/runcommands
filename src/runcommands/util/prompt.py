from rich.prompt import Confirm, Prompt, InvalidResponse

from .misc import abort
from .printer import printer


def prompt(message, password=False, choices=None, default=None, color=True):
    if color is True:
        color = "warning"
    if color:
        message = printer.colorize(message, color=color)
    try:
        return Prompt.ask(message, password=password, choices=choices, default=default)
    except KeyboardInterrupt:
        print()
        abort()


def confirm(
    prompt="Really?",
    color="warning",
    yes_value="y",
    abort_on_unconfirmed=False,
    abort_options=None,
):
    """Prompt for confirmation.

    Confirmation can be aborted by typing in a no value instead of one
    of the yes values or with Ctrl-C.

    Args:
        prompt (str): Prompt to present user ["Really?"]
        color (string|Color|bool) Color to print prompt string; can be
            ``False`` or ``None`` to print without color ["yellow"]
        yes_value (str): Value user must type in to confirm; note that
            this will be case sensitive *if* it contains any upper case
            letters ["y"]
        abort_on_unconfirmed (bool|int|str): When user does *not*
            confirm:

            - If this is an integer, print "Aborted" to stdout if
              it's 0 or to stderr if it's not 0 and then exit with
              this code
            - If this is a string, print it to stdout and exit with
              code 0
            - If this is ``True`` (or any other truthy value), print
              "Aborted" to stdout and exit with code 0

        abort_options (dict): Options to pass to :func:`abort` when not
            confirmed (these options will override any options set via
            ``abort_on_unconfirmed``)

    """
    if color:
        prompt = printer.colorize(prompt, color=color)

    choices = [yes_value, "n"]

    try:
        confirmed = Confirm.ask(prompt, choices=choices, default=False)
    except KeyboardInterrupt:
        print()
        confirmed = False

    # NOTE: The abort-on-unconfirmed logic is somewhat convoluted
    #       because of the special case for return code 0.

    do_abort_on_unconfirmed = not confirmed and (
        # True, non-zero return code, non-empty string, or any other
        # truthy value (in the manner of typical Python duck-typing)
        bool(abort_on_unconfirmed)
        or
        # Zero return code (special case)
        (abort_on_unconfirmed == 0 and abort_on_unconfirmed is not False)
    )

    if do_abort_on_unconfirmed:
        if abort_options is None:
            abort_options = {}

        if abort_on_unconfirmed is True:
            abort_options.setdefault("return_code", 0)
        elif isinstance(abort_on_unconfirmed, int):
            abort_options.setdefault("return_code", abort_on_unconfirmed)
        elif isinstance(abort_on_unconfirmed, str):
            abort_options.setdefault("message", abort_on_unconfirmed)
        else:
            abort_options.setdefault("return_code", 0)

        abort(**abort_options)

    return confirmed


class Confirm(Confirm):
    @property
    def validate_error_message(self):
        yes, no = self.choices
        return f"[prompt.invalid]Please enter {yes} or {no}"

    def render_default(self, default):
        """Default is *always* no."""
        return "(n)"

    def process_response(self, value):
        value = value.strip()
        # Hitting enter without a value -> "n" -> unconfirmed
        if not value:
            return False
        yes, no = self.choices
        # If yes value contains *any* upper case characters, do case-
        # sensitive yes value comparison
        all_lower = all(c.islower() for c in yes)
        if all_lower:
            value = value.lower()
        if value == yes:
            return True
        value = value.lower()
        # Allow "yes" when yes value is lower case "y"
        if yes == "y" and value == "yes":
            return True
        # Always allow "no"
        if value in ("n", "no"):
            return False
        raise InvalidResponse(self.validate_error_message)
