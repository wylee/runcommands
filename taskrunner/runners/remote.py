from .base import Runner

from .local import LocalRunner


class RemoteRunner(Runner):

    def run(self, cmd, host, user=None, cd=None, path=None, prepend_path=None,
            append_path=None, sudo=False, run_as=None, echo=False, hide=None, timeout=30,
            debug=False):
        ssh_connection_str = '{user}@{host}'.format(user=user, host=host) if user else host

        munge_path = path or prepend_path or append_path

        if munge_path:
            path = [path] if path else ['$PATH']
            if prepend_path:
                path = [prepend_path] + path
            if append_path:
                path += [append_path]
            path = ':'.join(path)

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

        # ssh -T someone@somehost sudo -u svusrXYZ bash <<'EOBASH'
        #     cd <cd> || exit 1
        #     export PATH="<path>"
        #     <cmd>
        # EOBASH
        ssh_cmd = ['ssh', '-T', ssh_connection_str, remote_cmd]

        local_runner = LocalRunner()
        return local_runner.run(ssh_cmd, echo=echo, hide=hide, timeout=timeout, debug=debug)
