import atexit
import os
import sys
import textwrap
import time
from functools import partial
from select import select
from shutil import get_terminal_size

import paramiko
from paramiko.agent import AgentRequestHandler
from paramiko.client import AutoAddPolicy, SSHClient
from paramiko.config import SSHConfig, SSH_PORT
from paramiko.ssh_exception import SSHException

from ..command import command
from ..util import abort, args_to_str, format_if, paths_to_str, printer, Hide
from .base import Runner
from .exc import RunAborted, RunError, RunValueError
from .result import Result


DEFAULT_SSH_PORT = SSH_PORT
DEFAULT_SSH_CONFIG_PATH = '~/.ssh/config'


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

        if debug:
            printer.hr(color='debug')
            printer.debug('REMOTE COMMAND:')
            printer.debug(textwrap.indent(remote_command, ' ' * 4))

        if echo:
            printer.hr(color='echo')
            printer.echo('RUNNING:', cmd)
            printer.echo('     ON:', host)
            if sudo:
                printer.echo('     AS:', 'sudo')
            elif run_as:
                printer.echo('     AS:', run_as)
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
            client, config = self.get_client(host, user, debug=debug)
            channel = self.get_channel(client, get_pty=use_pty, timeout=timeout)
            forwarder = AgentRequestHandler(channel) if config['forwardagent'] else None
            channel.exec_command(remote_command)
            reset_stdin = self.unbuffer_stdin(sys.stdin)

            send_stdin = partial(
                self.send, channel.send_ready, channel.sendall, sys.stdin, sys.stdout, use_pty)

            recv_stdout = partial(
                self.recv, channel.recv_ready, channel.recv, chunk_size, out_buffer, sys.stdout,
                hide_stdout)

            recv_stderr = partial(
                self.recv, channel.recv_stderr_ready, channel.recv_stderr, chunk_size, err_buffer,
                sys.stderr, hide_stderr)

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
                if forwarder is not None:
                    forwarder.close()
                channel.close()
                reset_stdin()
        except SSHException:
            if debug:
                raise
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

    def get_channel(self, client, timeout=None, get_pty=False, environment=None):
        channel = client._transport.open_session(timeout=timeout)
        if get_pty:
            width, height = get_terminal_size()
            channel.get_pty(width=width, height=height)
        channel.settimeout(timeout)
        if environment:
            channel.update_environment(environment)
        return channel

    def send(self, ready, send, source, mirror, use_pty):
        if ready():
            rlist, _, __ = select([source], [], [], 0)
            if source in rlist:
                text = source.read(1)
                if not use_pty:
                    mirror.write(text)
                send(text)
                return text

    def recv(self, ready, recv, num_bytes, buffer, mirror, hide, finish=False):
        if finish or ready():
            data = recv(num_bytes)
            if data:
                buffer.append(data)
                if not hide:
                    os.write(mirror.fileno(), data)
            return data

    @classmethod
    def get_client(cls, host, user=None, config_path=DEFAULT_SSH_CONFIG_PATH, debug=False):
        config = cls.get_host_config(host, config_path, debug)
        user = user or config.get('user')
        host = config['hostname']
        key = (host, user)
        if key not in cls.clients:
            client = SSHClient()
            client.load_system_host_keys()
            client.set_missing_host_key_policy(AutoAddPolicy())

            port = config['port']
            key_file = config.get('identityfile')

            if 'proxyjump' in config:
                proxy_host = config['proxyjump']
                proxy_client, proxy_config = cls.get_client(proxy_host, user, config_path, debug)
                proxy = proxy_client._transport.open_channel(
                    kind='direct-tcpip',
                    dest_addr=(host, port),
                    src_addr=('', 0),
                )
                if proxy_config['forwardagent']:
                    forwarder = AgentRequestHandler(proxy)

                    # XXX: Hacky
                    proxy_config['forwarder'] = forwarder
            else:
                proxy = None

            client.connect(host, port=port, username=user, key_filename=key_file, sock=proxy)

            cls.clients[key] = (client, config)
            if debug:
                printer.debug('Created SSH connection for {user}@{host}'.format_map(locals()))
        else:
            printer.debug('Using existing SSH connection for {user}@{host}'.format_map(locals()))
        return cls.clients[key]

    @classmethod
    def get_config(cls, config_path=DEFAULT_SSH_CONFIG_PATH, debug=False):
        config = SSHConfig()
        config_path = os.path.expanduser(config_path)
        config_path = os.path.expandvars(config_path)
        if os.path.isfile(config_path):
            with open(config_path) as fp:
                config.parse(fp)
        if debug:
            host_names = ', '.join(config.get_hostnames())
            printer.debug('Found SSH config for hosts:', host_names)
        return config

    @classmethod
    def get_host_config(cls, host, config_path=DEFAULT_SSH_CONFIG_PATH, debug=False):
        all_config = cls.get_config(config_path, debug)
        host_config = all_config.lookup(host)
        host_config['forwardagent'] = host_config.get('forwardagent', 'no').lower() == 'yes'
        host_config['port'] = int(host_config.get('port', DEFAULT_SSH_PORT))
        if debug:
            printer.debug('SSH config for {host}'.format(host=host), host_config)
        return host_config

    @classmethod
    def cleanup(cls):
        for client, config in cls.clients.values():
            # XXX: Hacky
            if 'forwarder' in config:
                config['forwarder'].close()

            client.close()


atexit.register(RemoteRunner.cleanup)


@command
def remote(config, cmd, host, user=None, cd=None, path=None, prepend_path=None,
           append_path=None, sudo=False, run_as=None, echo=False, hide=False, timeout=30,
           use_pty=True, abort_on_failure=True, inject_config=True):
    """Run a command on the remote host via SSH.

    Args:
        cmd (str|list): The command to run on the remote host; if it
            contains format strings, those will be filled from
            ``config``
        user (str): The user to log in as; command will be run as this
            user unless ``sudo`` or ``run_as`` is specified
        host (str): The remote host
        cd (str): Where to run the command on the remote host
        path (str|list): Replace ``$PATH`` on remote host with path(s)
        prepend_path (str|list): Add extra path(s) to front of remote
            ``$PATH``
        append_path (str|list): Add extra path(s) to end of remote
            ``$PATH``
        sudo (bool): Run as sudo?
        run_as (str): Run command as a different user with
            ``sudo -u <run_as>``
        inject_config (bool): Whether to inject config into the ``cmd``,
            ``host``, ``user``, ``cd``, the various path args, and
            ``run_as``

    """
    debug = config.run.debug
    format_kwargs = config if inject_config else {}
    path_converter = partial(paths_to_str, format_kwargs=format_kwargs)

    cmd = args_to_str(cmd, format_kwargs=format_kwargs)
    user = format_if(user, format_kwargs)
    host = format_if(host, format_kwargs)
    cd = format_if(cd, format_kwargs)
    run_as = format_if(run_as, format_kwargs)

    path = path_converter(path)
    prepend_path = path_converter(prepend_path)
    append_path = path_converter(append_path)

    runner = RemoteRunner()

    try:
        return runner.run(
            cmd, host, user=user, cd=cd, path=path, prepend_path=prepend_path,
            append_path=append_path, sudo=sudo, run_as=run_as, echo=echo, hide=hide,
            timeout=timeout, use_pty=use_pty, debug=debug)
    except RunAborted as exc:
        if debug:
            raise
        abort(1, str(exc))
    except RunError as exc:
        if abort_on_failure:
            abort(2, 'Remote command failed with exit code {exc.return_code}'.format_map(locals()))
        return exc
