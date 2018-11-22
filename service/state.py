import os
import asyncio
from collections import deque
from random import randint
import json

DEFAULT_USER = os.environ.get('DEFAULT_USER', 'guest')
DEFAULT_PASSWORD = os.environ.get('DEFAULT_PASSWORD', 'guest')


class WaitTimeout(Exception):
    pass


class State:
    def __init__(self):
        self._users = {
            DEFAULT_USER: DEFAULT_PASSWORD,
        }
        self._exchanges = {}
        self._queues = {}
        self._queues_bound_exhanges = {}
        self._authentication_tried_on = {}
        self._message_acknowledged = set()

    def check_credentials(self, username, password):
        is_authentified = self._users.get(username, None) == password

        # we "log" it for instrumentation purpose
        self._authentication_tried_on[username] = is_authentified

        return is_authentified

    def declare_exchange(self, exchange_name, exchange_type):
        if exchange_name not in self._exchanges:
            print("****exchange", exchange_name, "type", exchange_type)
            self._exchanges[exchange_name] = {
                'type': exchange_type,
                'messages': [],
            }
            return True

        # if redeclared with a different type => error
        return self._exchanges[exchange_name]['type'] == exchange_type

    def declare_queue(self, queue_name):
        if queue_name not in self._queues:
            self._queues[queue_name] = {
                'messages': deque(),
                'consumers': {},
            }

        return (
            True,  # ok
            0,  # message count
            0,  # consumer count
        )

    def bind_queue(self, queue, with_exchange):
        if with_exchange not in self._exchanges:
            return False

        if queue not in self._queues:
            return False

        if with_exchange in self._queues_bound_exhanges:
            self._queues_bound_exhanges[with_exchange].add(queue)
            return True

        self._queues_bound_exhanges[with_exchange] = {queue} # set()
        return True

    def register_consumer(
        self,
        consumer,
        consumer_tag,
        queue_name,
        channel_number
    ):
        if queue_name not in self._queues:
            return False

        self._queues[queue_name]['consumers'][consumer_tag] = {
            'transport': consumer,
            'channel_number': channel_number,
        }
        return True

    def delete_messages_of_queue(self, queue_name):
        queue = self._queues.get(queue_name, None)
        if queue is None:
            return
        queue['messages'] = deque()

    def get_messages_of_queue(self, queue_name):
        queue = self._queues.get(queue_name, None)
        if queue is None:
            return None
        return list(queue['messages'])

    def get_messages_of_exchange(self, exchange_name):
        exchange = self._exchanges.get(exchange_name, None)
        if exchange is None:
            return None
        return list(exchange['messages'])

    def store_message(
        self,
        exchange_name,
        headers,
        message_data,
    ):
        """Store message for inspection."""
        if exchange_name not in self._exchanges:
            return False

        message = {
            'headers': headers,
            'body': message_data.decode('utf-8'),
        }

        self._exchanges[exchange_name]['messages'].append(message)

        queues =  self._queues_bound_exhanges.get(
            exchange_name,
            set(),
        )
        for queue_name in queues:
            self._queues[queue_name]['messages'].append(message)

        return True

    def publish_message(
        self,
        exchange_name,
        headers,
        message_data,
    ):
        """Publish message to a worker without storing it."""
        if exchange_name not in self._exchanges:
            return None
        queues =  self._queues_bound_exhanges.get(
            exchange_name,
            set(),
        )
        for queue_name in queues:
            consumers = self._queues[queue_name]['consumers']
            for consumer_tag, consumer in consumers.items():
                delivery_tag = randint(1, 2**31)
                consumer['transport'].push_message(
                    headers,
                    message_data,
                    consumer['channel_number'],
                    consumer_tag,
                    delivery_tag,
                    exchange_name,
                )
                # TODO: support several delivery_tag
                # if exchange is plugged to several queues
                return delivery_tag

    def message_ack(self, delivery_tag):
        self._message_acknowledged.add(delivery_tag)

    async def wait_authentication_performed_on(self, username, timeout=10):
        for _ in range(timeout):
            decoded_username = username.decode('utf-8')
            if decoded_username in self._authentication_tried_on:
                return self._authentication_tried_on[decoded_username];

            await asyncio.sleep(1)

        raise WaitTimeout()

    async def wait_message_acknoledged(self, delivery_tag, timeout=10):
        for _ in range(timeout):
            if delivery_tag  in self._message_acknowledged:
                return True

            await asyncio.sleep(1)

        raise WaitTimeout()

    async def wait_queue_bound(self, queue, exchange, timeout=10):
        for _ in range(timeout):

            queues =  self._queues_bound_exhanges.get(
                exchange,
                set(),
            )

            if queue in queues:
                return True

            await asyncio.sleep(1)

        raise WaitTimeout()
