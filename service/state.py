import asyncio


class WaitTimeout(Exception):
    pass


class State:
    def __init__(self):
        self._users = {
            'guest': 'guest',
        }
        self._authentication_tried_on = {}

    def check_credentials(self, username, password):
        is_authentified = self._users.get(username, None) == password

        # we "log" it for instrumentation purpose
        self._authentication_tried_on[username] = is_authentified

        return is_authentified

    async def wait_authentication_performed_on(self, username, timeout=10):
        for _ in range(timeout):
            decoded_username = username.decode('utf-8')
            if decoded_username in self._authentication_tried_on:
                return self._authentication_tried_on[decoded_username];

            await asyncio.sleep(1)

        raise WaitTimeout()
