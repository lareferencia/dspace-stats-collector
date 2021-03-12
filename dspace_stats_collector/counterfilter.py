#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

import json
import re

class COUNTERRobotsFilter:

    def __init__(self, configContext):
        self.configContext = configContext
        self.counterRobots = self._readCOUNTERRobots(configContext.counterRobotsFilename)

    def _readCOUNTERRobots(self, filename):
        with open(filename) as json_file:
            counterRobotsList = json.load(json_file)

        for p in counterRobotsList:
            p['compiled_re'] = re.compile(p['pattern'])

        return counterRobotsList

    def run(self, events):

        for event in events:

            user_agent = event._src.get('userAgent', None)
            logger.debug('Event timestamp: {}'.format(event._src['time']))

            # temporaly accept all events from DSpace 4 and no userAgent data
            if user_agent is None and self.configContext.dspaceMajorVersion == '4': 
                #event.is_robot = False
                yield event 
            else:
                is_robot = False

                # searh for robots
                for robot in self.counterRobots:
                    is_robot = user_agent is None or robot['compiled_re'].search(user_agent) != None
                    if is_robot:
                        break

                logger.debug('COUNTER_FILTER:: Event: {} Agent: {} is_robot:{}'.format(event._id, user_agent, is_robot))

                # yield event only if not is a robot, else is discarted 
                #if not is_robot:
                #    yield event
                event.is_robot = is_robot
                yield event

            