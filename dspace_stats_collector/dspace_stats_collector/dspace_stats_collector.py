# -*- coding: utf-8 -*-

"""Main module."""

class Event:

    _data_dict = {}

    def __init__(self):
        None        

    def __getattr__(self, attribute):
        return self._data_dict[attribute]

    def __setattr__(self, name, value):
        self._data_dict[name] = value

    def __str__(self):
        return self._data_dict.__str__()
    


class EventPipeline:

    _input_stage = None
    _filters_stage = []
    _output_stage = None

    def __init__(self, input, filters, output):
        self._input_stage = input
        self._filters_stage = filters
        self._output_stage = output

    def run(self):
        events = self._input_stage.run() 

        for filter in self._filters_stage:
            events = filter.run(events)

        self._output_stage.run(events)


class DummyInput:

    def __init__(self):
        None
        
    def run(self):
        for x in range(1,50 ):
            e = Event()
            e.id = '00' + str(x)
            yield e


class DummyFilter:

    def __init__(self):
        None
        
    def run(self, events):
        print(events)

        for event in events:
            event.url = "http://dummy.org/" + event.id
            yield event

class DummyOutput:

    def __init__(self):
        None
        
    def run(self, events):
        for event in events:
            print(event)


dummy_pipeline = EventPipeline(DummyInput(), [DummyFilter()], DummyOutput())