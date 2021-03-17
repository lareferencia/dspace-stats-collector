#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Event pipeline classes  """

import logging
logger = logging.getLogger()

import json
import traceback

from itertools import tee


class Event:

    _data_dict = {}

    def __init__(self):
        None

    def __getattr__(self, attribute):
        return self._data_dict.get(attribute, None)

    def __setattr__(self, name, value):
        self._data_dict[name] = value

    def __str__(self):
        return self._data_dict.__str__()

    def toJSON(self):
        return json.dumps(self._data_dict, indent=4, sort_keys=True)

class EventPipeline:

    _input_stage = None
    _filters_stage = []
    _output_stage = None

    def __init__(self, input, filters, outputs):
        self._input_stage = input
        self._filters_stage = filters
        self._output_stage = outputs

    def run(self):
        events = self._input_stage.run()

        for filter in self._filters_stage:
            events = filter.run(events)            

        try:
            self._output_stage.run(events)
        except Exception as e: 
            logger.error( 'A fatal exception ocurred processing events !!!! {}'.format(e) )
            traceback.print_exc()



        """    
        # create and event iterator for every output (tee return tuple of size n)
        events_iter = tee(events, len(self._output_stage)) 
       
        # run each output stage on each event iterator
        for (output, teed_events) in zip(self._output_stage, events_iter):
            try:
                output.run(teed_events)
            except Exception as e: 
                logger.error( 'A fatal exception ocurred processing events !!!! {}'.format(e) )
                traceback.print_exc()
        """