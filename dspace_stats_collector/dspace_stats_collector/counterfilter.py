#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Session pipeline components """

import logging
logger = logging.getLogger()

import json
import re

class COUNTERRobotsFilter:

    def __init__(self, configContext):
        self.counterRobots = self._readCOUNTERRobots(configContext.counterRobotsFilename)

    def _readCOUNTERRobots(self, filename):
        with open(filename) as json_file:
            counterRobotsList = json.load(json_file)

        for p in counterRobotsList:
            p['compiled_re'] = re.compile(p['pattern'])

        return counterRobotsList

    def run(self, events):

        for event in events:
            
            is_robot = False
            user_agent = event._src['userAgent']

            # searh for robots
            for robot in self.counterRobots:
                is_robot = is_robot or robot['compiled_re'].search(user_agent)
                if is_robot:
                    logger.debug('Robot detected {}'.format(user_agent))
                    break
            
            # yield event only if not is a robot, else is discarted 
            if not is_robot:
                yield event
