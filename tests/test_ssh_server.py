
import asyncio
import asyncssh

class MySSHServer(asyncssh.SSHServer):
    def connection_made(self, conn):
        print('SSH connection received from %s.' % conn.get_extra_info('peername')[0])

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        if username == 'user' and password == 'pass':
            return True
        return False

    def auth_completed(self):
        print('Authentication completed.')

async def start_server():
    await asyncssh.create_server(MySSHServer, '', 2222,
                                 server_host_keys=['keys/ssh_host_rsa'],
                                 password_auth=True)

if __name__ == '__main__':
    # Generate keys first if they don't exist
    import os
    if not os.path.exists('keys'):
        os.makedirs('keys')
    if not os.path.exists('keys/ssh_host_rsa'):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with open('keys/ssh_host_rsa', 'wb') as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(start_server())
        print("Test SSH server running on port 2222")
        loop.run_forever()
    except (OSError, asyncssh.Error) as exc:
        import sys
        sys.exit('Error starting server: ' + str(exc))
    except KeyboardInterrupt:
        pass
