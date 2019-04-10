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

## What are the HTTP call availables

  * `DELETE /messages-in-queue/$QUEUE_NAME` purge messages of the given queue
  * `DELETE /messages-in-exchange/$EXCHANGE_NAME` purge messages of the given exchanges

  * `GET /authentification-done-with-success-on/$USERNAME` return if a client has successfully connected with the given username
  * `GET /messages-acknowledged/$DELIVERY_TAG` this call will block until the given delivery tag was acknowledged as consumed by a worker, if the message has already been consumed before the call, the call directly returns. => this call is super pratical to write your integration tests (i.e to check if you worker has written a record in database after the message was consumed)
  * `GET /messages-not-acknowledged/$DELIVERY_TAG` this call will block until the given delivery tag was marked as rejected by a worker (basic_nack), if the message has already been rejected before the call, the call directly returns. => this call is super practical to write your integration tests (i.e worker rejected the message for any reason)
  * `GET /messages-requeued/$DELIVERY_TAG` this call will block until the given delivery tag was marked as rejected by a worker with requeue parameter to true (basic_nack with requeue), if the message has already been requeued before the call, the call directly returns. => this call is super practical to write your integration tests (i.e worker rejected the message to be treated later)
  * `GET /messages-in-queue/$QUEUE_NAME` get all the messages waiting to be consumed in a given queue
  * `GET /messages-in-exchange/$EXCHANGE_NAME` get all the messages waiting to be consumed in a given exchange
  * `GET /queue-bound-to-exchange/$QUEUE_NAME/$EXCHANGE_NAME` wait until a given queue is bound to the given exchange

  * `POST  /add-message-on/$EXCHANGE_NAME` simulate the publishing of a message on a given exchange, the body of the POST is a json with a `headers`  and `body` fields
  * `POST  /add-message-in-queue/$QUEUE_NAME` simulate the publishing of a message on a given queue, the body of the POST is a json with a `headers`  and `body` fields
  * `POST /create-exchange/$EXCHANGE_NAME` simulate the creation of an exchange
  * `POST /create-queue/$QUEUE_NAME` simulate the creation of a queue

## Special thanks

For https://github.com/celery/py-amqp out of which I've extracted the type (de)serialization code
