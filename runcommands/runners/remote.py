import atexit
import getpass
import locale
import sys
from time import sleep

try:
    import paramiko
except ImportError:
    paramiko = None
else:
    from paramiko.client import AutoAddPolicy, SSHClient
    from paramiko.ssh_exception import SSHException

from ..util import Hide, printer
from .base import Runner
from .exc import RunError
from .local import LocalRunner
from .result import Result
from .streams import NonBlockingStreamReader


__all__ = ['RemoteRunnerParamiko', 'RemoteRunnerSSH']


class RemoteRunner(Runner):

    def get_remote_command(self, cmd, user, cd, path, sudo, run_as):
        remote_cmd = []

        if sudo:
            remote_cmd.append('sudo')
        elif run_as and run_as != user:
            remote_cmd.append('sudo -u {run_as}'.format(run_as=run_as))

        bash_cmd = ["bash <<'EOBASH'"]
        if cd:
            bash_cmd.append('  cd {cd} || exit 1\n'.format(cd=cd))
        if path:
            bash_cmd.append('  export PATH="{path}"\n'.format(path=path))
        bash_cmd.append('  {cmd}'.format(cmd=cmd))
        bash_cmd.append('EOBASH')
        bash_cmd = '\n'.join(bash_cmd)
        remote_cmd.append(bash_cmd)

        remote_cmd = ' '.join(remote_cmd)

        return remote_cmd

    def get_encoding(self):
        return locale.getpreferredencoding(do_setlocale=False)

    def munge_path(self, path, prepend_path, append_path):
        if path is prepend_path is append_path is None:
            return None
        path = [path] if path else ['$PATH']
        if prepend_path:
            path = [prepend_path] + path
        if append_path:
            path += [append_path]
        path = ':'.join(path)
        return path


class RemoteRunnerSSH(RemoteRunner):

    def run(self, cmd, host, user=None, cd=None, path=None, prepend_path=None,
            append_path=None, sudo=False, run_as=None, echo=False, hide=None, timeout=30,
            debug=False):
        # Runs a remote command by running ssh in a subprocess:
        #
        # ssh -T someone@somehost sudo -u svusrXYZ bash <<'EOBASH'
        #     cd <cd> || exit 1
        #     export PATH="<path>"
        #     <cmd>
        # EOBASH
        ssh_connection_str = '{user}@{host}'.format(user=user, host=host) if user else host
        path = self.munge_path(path, prepend_path, append_path)
        remote_command = self.get_remote_command(cmd, user, cd, path, sudo, run_as)
        ssh_cmd = ['ssh', '-T', ssh_connection_str, remote_command]
        local_runner = LocalRunner()
        return local_runner.run(ssh_cmd, echo=echo, hide=hide, timeout=timeout, debug=debug)


class RemoteRunnerParamiko(RemoteRunner):

    clients = {}

    def __init__(self, *args, **kwargs):
        if paramiko is None:
            raise RuntimeError('Paramiko remote strategy unusable: paramiko not installed')
        super().__init__(*args, **kwargs)

    def run(self, cmd, host, user=None, cd=None, path=None, prepend_path=None,
            append_path=None, sudo=False, run_as=None, echo=False, hide=None, timeout=30,
            debug=False):
        user = user or getpass.getuser()
        path = self.munge_path(path, prepend_path, append_path)
        remote_command = self.get_remote_command(cmd, user, cd, path, sudo, run_as)

        hide_stdout = Hide.hide_stdout(hide)
        hide_stderr = Hide.hide_stderr(hide)
        echo = echo and not hide_stdout

        if echo:
            printer.hr(color='echo')
            printer.echo('RUNNING:', cmd)
            if cd:
                printer.echo('    CWD:', cd)
            if path:
                printer.echo('   PATH:', path)
            printer.hr(color='echo')

        client = self.get_client(host, user, debug=debug)

        try:
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(host, username=user)
            channel, stdin, stdout, stderr = self.exec_command(
                client, remote_command, timeout=timeout)
            out = NonBlockingStreamReader('out', stdout, [], hide_stdout, sys.stdout)
            err = NonBlockingStreamReader('err', stderr, [], hide_stderr, sys.stderr)
            while not channel.exit_status_ready():
                sleep(0.1)
            out.finish()
            err.finish()
        except SSHException:
            raise RunError(-255, '', '')

        return_code = channel.exit_status
        out_str = out.get_string()
        err_str = err.get_string()

        if return_code:
            raise RunError(return_code, out_str, err_str)

        return Result(return_code, out_str, err_str)

    def exec_command(self, client, command, bufsize=-1, timeout=None, get_pty=False,
                     environment=None):
        # This is a copy of paramiko.client.SSHClient.exec_command().
        channel = client._transport.open_session(timeout=timeout)
        if get_pty:
            channel.get_pty()
        channel.settimeout(timeout)
        if environment:
            channel.update_environment(environment)
        channel.exec_command(command)
        stdin = channel.makefile('wb', bufsize)
        stdout = channel.makefile('r', bufsize)
        stderr = channel.makefile_stderr('r', bufsize)
        return channel, stdin, stdout, stderr

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


atexit.register(RemoteRunnerParamiko.cleanup)
