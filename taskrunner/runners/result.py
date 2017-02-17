
class Result:

    def __init__(self, return_code, stdout, stderr):
        self.return_code = return_code
        self.stdout = stdout
        self.stderr = stderr
        self.succeeded = self.return_code == 0
        self.failed = not self.succeeded
        self.stdout_lines = stdout.splitlines() if stdout else []
        self.stderr_lines = stderr.splitlines() if stderr else []
