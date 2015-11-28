# -*- coding: utf-8 -*-


import paramiko
import spur
import spur.ssh


class SSH(spur.SshShell):

    def _connect_ssh(self):
        if self._client is None:
            if self._closed:
                raise RuntimeError("Shell is closed")
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(spur.ssh.MissingHostKey.accept)
            client.connect(
                hostname=self._hostname,
                port=self._port,
                username=self._username,
                password=self._password,
                key_filename=self._private_key_file,
                look_for_keys=self._look_for_private_keys,
                timeout=self._connect_timeout
            )

            # Patch transport for faster SSH
            # https://github.com/paramiko/paramiko/issues/175
            transport = client.get_transport()
            transport.window_size = 2147483647
            transport.packetizer.REKEY_BYTES = pow(2, 40)
            transport.packetizer.REKEY_PACKETS = pow(2, 40)

            self._client = client
        return self._client


def get_ssh(hostname):
    return SSH(hostname, shell_type=spur.ssh.ShellTypes.sh)
