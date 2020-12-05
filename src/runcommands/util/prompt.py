from .misc import abort
from .printer import printer


def confirm(
    prompt="Really?",
    color="warning",
    yes_values=("y", "yes"),
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
        yes_values (list[str]): Values user must type in to confirm
            [("y", "yes")]
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
    if isinstance(yes_values, str):
        yes_values = (yes_values,)

    prompt = f"{prompt} [{yes_values[0]}/N] "

    if color:
        prompt = printer.colorize(prompt, color=color)

    try:
        answer = input(prompt)
    except KeyboardInterrupt:
        print()
        confirmed = False
    else:
        answer = answer.strip().lower()
        confirmed = answer in yes_values

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


def prompt(message, default=None, color=True):
    message = message.rstrip()
    if default is not None:
        default = default.rstrip()
        message = "%s [%s]" % (message, default)
    message = "%s " % message
    if color is True:
        color = "warning"
    if color:
        message = printer.colorize(message, color=color)
    try:
        value = input(message)
    except KeyboardInterrupt:
        print()
        abort()
    value = value.strip()
    if not value and default is not None:
        return default
    return value
