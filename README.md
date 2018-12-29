# mock-amqp-server

![](https://img.shields.io/docker/build/allansimon/mock-amqp-server.svg)

Instrumented mock amqp (with some work to be RabbitMQ compatible) server to test your publisher/consumer at the network level

## What does this propose ?
Addmitting  you have a worker you want to test, you spin this test infrastructure:

````
[ mock amqp server]<--- port 5672 --->[ your worker not instrumented]<----network-->[ database ]
        ^                                                                               ^   
        |                                                                               |
    connection on port 80                                                               |
        |                                                                               |
[ test running on the side] -------------------------------------------------------------
 ````

It permits you to have this in your CI tests  (in pseudo code)

```python

def test_worker_insert_valid_message_in_database():
    database_connection = create_connection_to_database()
    backdoor_amqp = connection_to_amqp_backdoor()
    
    backdoor_amqp.insert_message(message_id=42, text="hello",in_queue="messages_to_treat")
    backdoor_amqp.wait_message_being_ack(message_id=42, timeout=5)
    
    database_connection.assert_row_exists(id="42", content="hello") 

```

Without needing to modify your worker code

## Why this ?

I recently worked on RabbitMQ worker, the unit tests were all good, 95% tests coverage ... BUT IT WAS NOT WORKING

How ? While refactoring I simply inverted the line 

```
worker.start_infinite_loop()
worker.on_receive(worker.treat_message())
```

Which would cause the message of the actual queue not being treated as the callback was not registered when the worker started ...

> Simply mock your AMQP library

Ok, what about this one ?

The day after while refactoring and switching the code configuration from `command-line arguments` to `environment variables` , the CPU was hitting 100%, no message being treated

After some searching, it was a bug in the 3rd party library and my code, that was not handling the "wrong password" error correctly. Which was not found in CI because the mock library had not this problem.

## Special thanks

For https://github.com/celery/py-amqp out of which I've extracted the type (de)serialization code
