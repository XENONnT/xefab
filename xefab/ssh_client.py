import paramiko
from paramiko.ssh_exception import SSHException


class SSHClient(paramiko.SSHClient):
    password = None

    def _2fa_handler(self, title, instructions, prompt_list):
        if not prompt_list:
            return []
        if "Password:" in prompt_list[0][0] and self.password is not None:
            return [self.password]
        if "Duo two-factor login" in prompt_list[0][0]:
            return ["1"]

    def _auth(
        self,
        username,
        password,
        pkey,
        key_filenames,
        allow_agent,
        look_for_keys,
        gss_auth,
        gss_kex,
        gss_deleg_creds,
        gss_host,
        passphrase,
    ):
        """
        Try, in order:
            - The key(s) passed in, if one was passed in.
            - Any key we can find through an SSH agent (if allowed).
            - Any "id_rsa", "id_dsa" or "id_ecdsa" key discoverable in ~/.ssh/
              (if allowed).
            - Plain username/password auth, if a password was given.
        (The password might be needed to unlock a private key [if 'passphrase'
        isn't also given], or for two-factor authentication [for which it is
        required].)
        """

        self.password = password
        if self.password is not None:
            try:
                self._transport.auth_interactive(username, self._2fa_handler)
                return
            except SSHException as e:
                pass

        super()._auth(
            username=username,
            password=password,
            pkey=pkey,
            key_filenames=key_filenames,
            allow_agent=allow_agent,
            look_for_keys=look_for_keys,
            gss_auth=gss_auth,
            gss_kex=gss_kex,
            gss_deleg_creds=gss_deleg_creds,
            gss_host=gss_host,
            passphrase=passphrase,
        )


paramiko.client.SSHClient = SSHClient
