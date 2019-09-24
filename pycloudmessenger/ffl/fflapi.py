#!/usr/bin/env python3
#author mark_purcell@ie.ibm.com

"""FFL protocol handler.
/*
 * Licensed to the Apache Software Foundation (ASF) under one or more
 * contributor license agreements.  See the NOTICE file distributed with
 * this work for additional information regarding copyright ownership.
 * The ASF licenses this file to You under the Apache License, Version 2.0
 * (the "License"); you may not use this file except in compliance with
 * the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

Please note that the following code was developed for the project MUSKETEER
in DRL funded by the European Union under the Horizon 2020 Program.
"""

# pylint: disable=R0903, R0913

import json
import logging
import requests

import pycloudmessenger.rabbitmq as rabbitmq
import pycloudmessenger.serializer as serializer
import pycloudmessenger.ffl.message_catalog as catalog

logging.getLogger("pika").setLevel(logging.WARNING)


class Context(rabbitmq.RabbitContext):
    """
        Holds connection details for an FFL service
    """


class TimedOutException(rabbitmq.RabbitTimedOutException):
    '''Over-ride exception'''

class ConsumerException(rabbitmq.RabbitConsumerException):
    '''Over-ride exception'''


class Messenger(rabbitmq.RabbitDualClient):
    """
        Communicates with an FFL service
    """
    def __init__(self, context: Context, publish_queue: str = None, subscribe_queue: str = None):
        """
            Class initializer
        """
        super(Messenger, self).__init__(context)

        #Keep a copy here - lots of re-use
        self.timeout = context.timeout()

        #Publish not over-ridden so use context version
        if not publish_queue:
            publish_queue = context.feeds()

        self.start_subscriber(queue=rabbitmq.RabbitQueue(subscribe_queue))
        self.start_publisher(queue=rabbitmq.RabbitQueue(publish_queue))

        #Initialise the catalog with the target subscribe queue
        self.catalog = catalog.MessageCatalog(context.user(), self.get_subscribe_queue())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()

    def _send(self, message: dict, queue: str = None):
        '''
        Send a message and return immediately
        Throws: An exception on failure
        Returns: dict
        '''
        pub_queue = rabbitmq.RabbitQueue(queue) if queue else None
        super(Messenger, self).send(serializer.Serializer.serialize(message), pub_queue)

    def _receive(self, timeout: int = 0) -> dict:
        '''
        Wait for timeout seconds for a message to arrive
        Throws: An exception on failure
        Returns: dict
        '''
        if not timeout:
            timeout = self.timeout

        try:
            super(Messenger, self).receive(self.internal_handler, timeout, 1)
        except rabbitmq.RabbitTimedOutException as exc:
            raise TimedOutException(exc) from exc
        except rabbitmq.RabbitConsumerException as exc:
            raise ConsumerException(exc) from exc
        return serializer.Serializer.deserialize(self.last_recv_msg)

    def _invoke_service(self, message: dict, timeout: int = 0) -> dict:
        '''
        Send a message and wait for a reply
        Throws: An exception on failure
        Returns: dict
        '''

        result = None
        if not timeout:
            timeout = self.timeout

        try:
            message = serializer.Serializer.serialize(message)
            result = super(Messenger, self).invoke_service(message, timeout)
        except rabbitmq.RabbitTimedOutException as exc:
            raise TimedOutException(exc) from exc
        except rabbitmq.RabbitConsumerException as exc:
            raise ConsumerException(exc) from exc

        if not result:
            raise Exception(f"Malformed object: None")
        result = serializer.Serializer.deserialize(result)

        if 'error' in result:
            raise Exception(result['error'])

        if 'calls' not in result:
            raise Exception(f"Malformed object: {result}")

        results = result['calls'][0]['count'] #calls[0] will always succeed
        return result['calls'][0]['data'] if results else None

    def _dispatch_model(self, model: dict = None):
        '''
        Dispatch a model and determine its download location
        Throws: An exception on failure
        Returns: dict
        '''

        if not model:
            return {}

        #First, obtain the upload location/keys
        message = self.catalog.msg_bin_uploader()
        upload_info = self._invoke_service(message)

        #And then perform the upload
        response = requests.post(
                        upload_info['url'],
                        files={'file': json.dumps(model)},
                        data=upload_info['fields'],
                        headers=None)

        if not response.ok:
            raise Exception(f'Upload Error: {response.status_code}')

        if 'key' not in upload_info['fields']:
            raise Exception('Malformed URL.')

        #Now obtain the download location/keys
        message = self.catalog.msg_bin_downloader(upload_info['fields']['key'])
        download_info = self._invoke_service(message)
        return {'url': download_info}

    ######## Public methods

    def user_create(self, user_name: str, password: str, organisation: str) -> dict:
        '''
        Register as a new user on the platformr
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_user_create(user_name, password, organisation)
        return self._invoke_service(message)

    def user_assignments(self) -> dict:
        '''
        Return all tasks joined by the current user
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_user_assignments()
        return self._invoke_service(message)

    def task_assignment_join(self, task_name: str) -> dict:
        '''
        As a potential task participant, try to join the task
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_join(task_name)
        message = self._invoke_service(message)
        return message[0]

    def task_assignment_update(self, task_name: str, status: str, model: dict = None):
        '''
        Sends an update, including a model dict, no reply wanted
        Throws: An exception on failure
        Returns: Nothing
        '''

        model_message = self._dispatch_model(model)

        message = self.catalog.msg_task_assignment_update(
                        task_name, status, model_message, want_reply=False)
        self._send(message)

    def task_assignment_wait(self, timeout: int = 0) -> dict:
        '''
        Wait for a message, until timeout seconds
        Throws: An exception on failure
        Returns: dict
        '''
        return self._receive(timeout)

    def task_assignments(self, task_name: str) -> dict:
        '''
        Return all assignments for the owned task
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_assignments(task_name)
        return self._invoke_service(message)

    def task_listing(self) -> dict:
        '''
        Return a list of all tasks available
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_listing()
        return self._invoke_service(message)

    def task_create(self, task_name: str, algorithm: str, quorum: int, adhoc: dict) -> dict:
        '''
        A new task created by the current user
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_create(task_name, algorithm, quorum, adhoc)
        message = self._invoke_service(message)
        return message[0]

    def task_update(self, task_name: str, status: str, algorithm: str = None,
                    quorum: int = -1, adhoc: dict = None) -> dict:
        '''
        Change task details
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_update(task_name, algorithm, quorum, adhoc, status)
        return self._invoke_service(message)

    def task_info(self, task_name: str) -> dict:
        '''
        Return info on a task
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_info(task_name)
        message = self._invoke_service(message)
        return message[0]

    def task_quit(self, task_name: str):
        '''
        As a task participant, leave the task
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_quit(task_name)
        return self._invoke_service(message)

    def task_start(self, task_name: str, model: dict = None) -> dict:
        '''
        As a task owner, start the task
        Throws: An exception on failure
        Returns: dict
        '''
        model_message = self._dispatch_model(model)
        message = self.catalog.msg_task_start(task_name, model_message)
        return self._invoke_service(message)

    def task_stop(self, task_name: str) -> dict:
        '''
        As a task owner, stop the task
        Throws: An exception on failure
        Returns: dict
        '''
        message = self.catalog.msg_task_stop(task_name)
        return self._invoke_service(message)
