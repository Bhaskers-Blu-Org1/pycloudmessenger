#!/usr/bin/env python3
#author markpurcell@ie.ibm.com

"""RabbitMQ helper class.
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
"""
"""
IBM-Review-Requirement: Art30.3 - DO NOT TRANSFER OR EXCLUSIVELY LICENSE THE FOLLOWING CODE UNTIL 30/11/2025!
Please note that the following code was developed for the project MUSKETEER in DRL funded by the European Union
under the Horizon 2020 Program.
The project started on 01/12/2018 and was completed on 30/11/2021. Thus, in accordance with article 30.3 of the
Multi-Beneficiary General Model Grant Agreement of the Program, the above limitations are in force until 30/11/2025.
"""

import logging
import json
import unittest
import pytest
import pycloudmessenger.ffl.fflapi as fflapi
import pycloudmessenger.ffl.abstractions as ffl
import pycloudmessenger.serializer as serializer


#Set up logger
logging.basicConfig(
    level=logging.INFO,
    #level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)-6s %(name)-16s :: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

LOGGER = logging.getLogger(__package__)


class MockAggregator(ffl.AbstractAggregator):
    """ This class provides the functionality needed by the
        aggregator of a federated learning task. """

    def __init__(self, context: ffl.AbstractContext, task_name: str = None):
        if not task_name:
            raise ValueError('Task name must be provided')

    def send(self, message: dict = None, participant: str = None) -> None:
        pass

    def receive(self, timeout: int = 0) -> dict:
        pass

    def get_participants(self) -> dict:
        pass

    def stop_task(self, model: dict = None) -> None:
        pass


class MockParticipant(ffl.AbstractParticipant):
    """ This class provides the functionality needed by the
        participant of a federated learning task. """

    def __init__(self, context: ffl.AbstractContext, task_name: str = None):
        if not task_name:
            raise ValueError('Task name must be provided')

    def send(self, message: dict = None) -> None:
        pass

    def receive(self, timeout: int = 0) -> dict:
        pass

    def leave_task(self) -> None:
        pass


@pytest.mark.usefixtures("credentials")
class FFLTests(unittest.TestCase):
    #@unittest.skip("temporarily skipping")
    def test_bad_factory(self):
        #No key
        with self.assertRaises(Exception):
            ffl.Factory.register(None, fflapi.Context, fflapi.User, fflapi.Aggregator, fflapi.Participant).context(None)
        #Bad key
        with self.assertRaises(Exception):
            ffl.Factory.register('', fflapi.Context, fflapi.User, fflapi.Aggregator, fflapi.Participant).context('')
        #No concrete Context
        with self.assertRaises(Exception):
            ffl.Factory.register('cloud', None, fflapi.User, fflapi.Aggregator, fflapi.Participant).context('cloud')
        #No concrete User
        with self.assertRaises(Exception):
            ffl.Factory.register('cloud', fflapi.Context, None, fflapi.Aggregator, fflapi.Participant).context('cloud')
        #No concrete Aggregator
        with self.assertRaises(Exception):
            ffl.Factory.register('cloud', fflapi.Context, fflapi.User, None, fflapi.Participant).context('cloud')
        #No concrete Participant
        with self.assertRaises(Exception):
            ffl.Factory.register('cloud', fflapi.Context, fflapi.User, fflapi.Aggregator, None).context('cloud')
        #No credentials
        with self.assertRaises(Exception):
            ffl.Factory.register('cloud', fflapi.Context, fflapi.User, fflapi.Aggregator, fflapi.Participant).context('cloud')

    #@unittest.skip("temporarily skipping")
    def test_factory_user(self):
        context = ffl.Factory.register(
                        'cloud', fflapi.Context, fflapi.User,
                        fflapi.Aggregator, fflapi.Participant).context('cloud', self.credentials)
        user = ffl.Factory.user(context)

    #@unittest.skip("temporarily skipping")
    def test_factory_aggregator(self):
        context = ffl.Factory.register(
                        'cloud', fflapi.Context, fflapi.User,
                        MockAggregator, fflapi.Participant).context('cloud', self.credentials)

        with self.assertRaises(ValueError):
            user = ffl.Factory.aggregator(context)

        user = ffl.Factory.aggregator(context, 'the-task')

    #@unittest.skip("temporarily skipping")
    def test_factory_participant(self):
        context = ffl.Factory.register(
                        'cloud', fflapi.Context, fflapi.User,
                        MockAggregator, MockParticipant).context('cloud', self.credentials)

        with self.assertRaises(ValueError):
            user = ffl.Factory.participant(context)

        user = ffl.Factory.participant(context, 'the-task')

    #@unittest.skip("temporarily skipping")
    def test_enum(self):
        self.assertTrue(ffl.Notification('aggregator_started') is ffl.Notification.aggregator_started)

        with self.assertRaises(ValueError):
            self.assertTrue(ffl.Notification('start') is ffl.Notification.aggregator_started)

        with self.assertRaises(ValueError):
            self.assertTrue(ffl.Notification('started') is ffl.Notification.aggregator_started)

        #Check list searching
        arr = [ffl.Notification.aggregator_started, ffl.Notification.aggregator_stopped]
        self.assertTrue(ffl.Notification('aggregator_started') in arr)
        self.assertTrue(ffl.Notification('participant_joined') not in arr)

    #@unittest.skip("temporarily skipping")
    def test_serializer(self):
        #Ensure serializability
        notify = {'type': ffl.Notification.participant_joined}
        s = serializer.JsonSerializer()
        serialized = s.serialize(notify)
        deserialized = s.deserialize(serialized)
        self.assertTrue(ffl.Notification(deserialized['type']) is ffl.Notification.participant_joined)

        s = serializer.JsonPickleSerializer()
        serialized = s.serialize(notify)
        deserialized = s.deserialize(serialized)
        self.assertTrue(ffl.Notification(deserialized['type']) is ffl.Notification.participant_joined)

        s = serializer.Base64Serializer()
        serialized = s.serialize(notify)
        deserialized = s.deserialize(serialized)
        self.assertTrue(ffl.Notification(deserialized['type']) is ffl.Notification.participant_joined)
