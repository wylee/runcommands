import atexit
import sys
import time
from functools import partial
from select import select
from shutil import get_terminal_size

import paramiko
from paramiko.client import AutoAddPolicy, SSHClient
from paramiko.ssh_exception import SSHException

from ..util import Hide, printer
from .base import Runner
from .exc import RunAborted, RunError, RunValueError
from .result import Result


class RemoteRunner(Runner):

    """Run a command on a remote host via SSH."""

    clients = {}

    def run(self, cmd, host, user=None, cd=None, path=None, prepend_path=None,
            append_path=None, sudo=False, run_as=None, echo=False, hide=False, timeout=30,
            use_pty=True, debug=False):
        if sudo and run_as:
            raise RunValueError('Only one of `sudo` or `run_as` may be specified')

        use_pty = self.use_pty(use_pty)
        path = self.munge_path(path, prepend_path, append_path, '$PATH')
        remote_command = self.get_command(cmd, user, cd, path, sudo, run_as)

        hide_stdout = Hide.hide_stdout(hide)
        hide_stderr = Hide.hide_stderr(hide)
        echo = echo and not hide_stdout

        if echo:
            printer.hr(color='echo')
            printer.echo('RUNNING:', cmd)
            printer.echo('     ON:', host)
            if cd:
                printer.echo('    CWD:', cd)
            if path:
                printer.echo('   PATH:', path)
            printer.hr(color='echo')

        out_buffer = []
        err_buffer = []

        chunk_size = 1024
        encoding = self.get_encoding()

        try:
            client = self.get_client(host, user, debug=debug)
            channel = self.exec_command(client, remote_command, get_pty=use_pty, timeout=timeout)

            reset_stdin = self.unbuffer_stdin(sys.stdin)

            send_stdin = partial(
                self.send, channel.send_ready, channel.sendall, sys.stdin, sys.stdout, use_pty,
                encoding)

            recv_stdout = partial(
                self.recv, channel.recv_ready, channel.recv, chunk_size, out_buffer, sys.stdout,
                encoding, hide_stdout)

            recv_stderr = partial(
                self.recv, channel.recv_stderr_ready, channel.recv_stderr, chunk_size, err_buffer,
                sys.stderr, encoding, hide_stderr)

            try:
                while not channel.exit_status_ready():
                    send_stdin()
                    recv_stdout()
                    recv_stderr()
                    sys.stdout.flush()  # Echo stdin immediately
                    time.sleep(paramiko.io_sleep)

                while recv_stdout(finish=True):
                    time.sleep(paramiko.io_sleep)

                while recv_stderr(finish=True):
                    time.sleep(paramiko.io_sleep)

                return_code = channel.recv_exit_status()
            except KeyboardInterrupt:
                if use_pty:
                    # Send end-of-text (AKA Ctrl-C)
                    channel.send('\x03')
                raise RunAborted('\nAborted')
            finally:
                channel.close()
                reset_stdin()
        except SSHException:
            raise RunError(-255, '', '', encoding)

        result_args = (return_code, out_buffer, err_buffer, encoding)

        if return_code:
            raise RunError(*result_args)

        return Result(*result_args)

    def get_command(self, cmd, user, cd, path, sudo, run_as):
        if sudo:
            run_as = 'sudo -s'
        elif run_as and run_as != user:
            run_as = 'sudo -u {run_as} -s'.format(run_as=run_as)
        else:
            run_as = ''

        eval_cmd = []

        if cd:
            eval_cmd.append('cd {cd}'.format(cd=cd))

        if path:
            eval_cmd.append('export PATH="{path}"'.format(path=path))

        eval_cmd.append(cmd)
        eval_cmd = ' &&\n    '.join(eval_cmd)

        remote_cmd = """
{run_as} eval $(cat <<'EOF'
    {eval_cmd}
EOF
)
"""
        remote_cmd = remote_cmd.format_map(locals())
        remote_cmd = remote_cmd.strip()

        return remote_cmd

    def exec_command(self, client, command, timeout=None, get_pty=False, environment=None):
        channel = client._transport.open_session(timeout=timeout)
        if get_pty:
            width, height = get_terminal_size()
            channel.get_pty(width=width, height=height)
        channel.settimeout(timeout)
        if environment:
            channel.update_environment(environment)
        channel.exec_command(command)
        return channel

    def send(self, ready, send, source, mirror, use_pty, encoding):
        if ready():
            rlist, _, __ = select([source], [], [], 0)
            if source in rlist:
                data = source.read(1)
                if not use_pty:
                    mirror.write(data.decode(encoding))
                send(data)
                return data

    def recv(self, ready, recv, num_bytes, buffer, mirror, encoding, hide, finish=False):
        if finish or ready():
            data = recv(num_bytes)
            if data:
                buffer.append(data)
                if not hide:
                    text = data.decode(encoding)
                    mirror.write(text)
            return data

    @classmethod
    def get_client(cls, host, user, debug=False):
        key = (host, user)
        if key not in cls.clients:
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(host, username=user)
            cls.clients[key] = client
            if debug:
                printer.debug('Created SSH connection for {user}@{host}'.format_map(locals()))
        else:
            printer.debug('Using existing SSH connection for {user}@{host}'.format_map(locals()))
        return cls.clients[key]

    @classmethod
    def cleanup(cls):
        for client in cls.clients.values():
            client.close()


atexit.register(RemoteRunner.cleanup)
