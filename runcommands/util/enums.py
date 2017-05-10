import enum


class Color(enum.Enum):

    none = ''
    reset = '\033[0m'
    black = '\033[90m'
    red = '\033[91m'
    green = '\033[92m'
    yellow = '\033[93m'
    blue = '\033[94m'
    magenta = '\033[95m'
    cyan = '\033[96m'
    white = '\033[97m'

    def __str__(self):
        return self.value


class Hide(enum.Enum):

    none = 'none'
    stdout = 'stdout'
    stderr = 'stderr'
    all = 'all'

    @classmethod
    def hide_stdout(cls, value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return cls(value) in (cls.stdout, cls.all)

    @classmethod
    def hide_stderr(cls, value):
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return cls(value) in (cls.stderr, cls.all)

    def __str__(self):
        return self.name
