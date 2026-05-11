=======
History
=======

Project background / OpenAIRE 2020
----------------------------------

DSpace Stats Collector started as a lightweight, easy-to-deploy, read-only
alternative for collecting DSpace usage events and sending them to a Matomo
compatible usage statistics infrastructure.

The original deployment model focused on individual repositories that needed to
share item views and downloads with an external regional aggregator. A regional
usage statistics service allows usage data to be shared across repositories,
e-journals, and CRIS systems for evaluation, management, and reporting. One of
the main project requirements was therefore to provide a friendly, non-invasive
deployment process for repository managers.

This work was developed as part of LA Referencia's activities in the OpenAIRE
Advance project, building a pilot for usage data exchange between Latin America
and Europe open science infrastructures.

The original design principles were:

* open-source, collaborative development;
* straightforward installation for non-expert Linux users without root or
  superuser privileges;
* sandboxed execution without system-wide package installation;
* lightweight operation that preserves repository stability and performance;
* compatibility with the OpenAIRE Usage Statistics Service;
* adaptability to other repository platforms and aggregator services.

Implementation highlights
~~~~~~~~~~~~~~~~~~~~~~~~~

The collector follows a pipe-and-filter architecture with input, filter, and
output stages. This design keeps each processing step independent so future
stages can be added for other platforms or usage services.

The initial pipeline included:

* DSpace Solr Statistics Input, which queries the DSpace Solr statistics core
  for usage events later than a configured or stored timestamp.
* COUNTER Robots Filter, which excludes robot and crawler traffic using Project
  COUNTER user-agent patterns.
* DSpace Database Filter, which enriches Solr events with item title,
  bitstream filename, handle, and OAI-PMH-related metadata from the DSpace
  relational database.
* Matomo API Filter, which transforms events into Matomo Tracking API
  parameters.
* Matomo Sender Output, which buffers and sends events through Matomo bulk
  tracking.

Credits
~~~~~~~

This component is part of an alternative DSpace Usage Statistics collector
strategy developed by LA Referencia, CONCYTEC (Peru), IBICT (Brazil), and
OpenAIRE as part of OpenAIRE Advance project WP5, Subtask 5.2.2, "Pilot common
methods for usage statistics across Europe & Latin America".

Historical references
~~~~~~~~~~~~~~~~~~~~~

* Schirrwagen, Jochen; Pierrakos, Dimitris; MacIntyre, Ross; Needham, Paul;
  Simeonov, Georgi; Principe, Pedro; and Dazy, Andre. (2017).
* OpenAIRE2020 - Usage Statistics Services - D8.5.
  https://doi.org/10.5281/zenodo.1034164
* Project COUNTER: https://www.projectcounter.org/
* Matomo Tracking API: https://developer.matomo.org/api-reference/tracking-api
* DSpace Statistics documentation:
  https://wiki.lyrasis.org/display/DSDOC3x/DSpace+Statistics

0.1.0 (2019-07-23)
------------------

* First release on PyPI.
