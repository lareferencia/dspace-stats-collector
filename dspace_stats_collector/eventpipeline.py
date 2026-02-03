#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Event pipeline classes  """

import logging
logger = logging.getLogger(__name__)

import json
import traceback
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterator, Generator, List, Optional


class Event:
    """
    Represents a single usage event flowing through the pipeline.
    
    IMPORTANT: Each Event instance has its own isolated _data_dict.
    This was fixed from a bug where _data_dict was a class variable,
    causing all events to share the same data dictionary.
    """
    __slots__ = ['_data_dict']

    def __init__(self) -> None:
        # Use object.__setattr__ to bypass our custom __setattr__
        object.__setattr__(self, '_data_dict', {})

    def __getattr__(self, attribute: str) -> Optional[Any]:
        try:
            data_dict = object.__getattribute__(self, '_data_dict')
            return data_dict.get(attribute, None)
        except AttributeError:
            return None

    def __setattr__(self, name: str, value: Any) -> None:
        try:
            data_dict = object.__getattribute__(self, '_data_dict')
            data_dict[name] = value
        except AttributeError:
            # This should only happen during __init__ before _data_dict exists
            object.__setattr__(self, name, value)

    def __str__(self) -> str:
        return str(object.__getattribute__(self, '_data_dict'))

    def toJSON(self) -> str:
        data_dict = object.__getattribute__(self, '_data_dict')
        return json.dumps(data_dict, indent=4, sort_keys=True)


# =============================================================================
# Abstract Base Classes for Pipeline Stages
# =============================================================================

class PipelineInput(ABC):
    """
    Abstract base class for pipeline input stages.
    
    Input stages are responsible for reading events from a source
    (e.g., Solr) and yielding Event objects.
    """
    
    @abstractmethod
    def run(self) -> Generator[Event, None, None]:
        """
        Generate events from the input source.
        
        Yields:
            Event: Usage events read from the source
        """
        pass


class PipelineFilter(ABC):
    """
    Abstract base class for pipeline filter stages.
    
    Filters transform, enrich, or filter out events as they
    pass through the pipeline.
    """
    
    @abstractmethod
    def run(self, events: Iterator[Event]) -> Generator[Event, None, None]:
        """
        Process events, optionally transforming or filtering them.
        
        Args:
            events: Iterator of incoming events
            
        Yields:
            Event: Processed events (may be filtered, enriched, or transformed)
        """
        pass


class PipelineOutput(ABC):
    """
    Abstract base class for pipeline output stages.
    
    Output stages consume events and send them to a destination
    (e.g., Matomo, file, Elasticsearch).
    """
    
    @abstractmethod
    def run(self, events: Iterator[Event]) -> None:
        """
        Consume events and send to destination.
        
        Args:
            events: Iterator of events to output
        """
        pass


class EventPipeline:
    """
    Orchestrates the flow of events through input, filter, and output stages.
    
    The pipeline follows the "pipe and filter" architecture pattern:
    1. Input stage generates events
    2. Filter stages process events sequentially
    3. Output stage sends events to destination
    """

    def __init__(
        self, 
        input_stage: PipelineInput, 
        filters: List[PipelineFilter], 
        output_stage: PipelineOutput
    ) -> None:
        """
        Initialize the event pipeline.
        
        Args:
            input_stage: Source of events
            filters: List of filters to apply in order
            output_stage: Destination for processed events
        """
        self._input_stage = input_stage
        self._filters_stage = filters
        self._output_stage = output_stage

    def run(self) -> None:
        """Execute the pipeline."""
        events = self._input_stage.run()

        for pipeline_filter in self._filters_stage:
            events = pipeline_filter.run(events)

        try:
            self._output_stage.run(events)
        except Exception as e:
            logger.error('A fatal exception occurred processing events: %s', e)
            traceback.print_exc()
            raise
