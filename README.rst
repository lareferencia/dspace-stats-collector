============================
Dspace usage stats collector
============================


.. image:: https://img.shields.io/pypi/v/dspace-stats-collector.svg
        :target: https://pypi.python.org/pypi/dspace-stats-collector

.. image:: https://img.shields.io/travis/lareferencia/dspace-stats-collector.svg
        :target: https://travis-ci.org/lareferencia/dspace-stats-collector

.. image:: https://readthedocs.org/projects/dspace-stats-collector/badge/?version=latest
        :target: https://dspace-stats-collector.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status
        
.. image:: https://img.shields.io/pypi/l/dspace-stats-collector.svg
        :target: https://pypi.python.org/pypi/dspace-stats-collector
        :alt: License


A python agent for sending DSpace usage statistics events to Matomo and ELK Stack. 


* Free software: GNU General Public License v3
* Documentation: https://dspace-stats-collector.readthedocs.io.


Standalone user level installing (w/ python bundle)
--------------------------------------------------
This is the recommended installation method, the instalation script :

* Downloads and install Miniconda (x86 or x64) a free minimal installer for conda/python (https://docs.conda.io/en/latest/miniconda.html) in CURRENT_USER_HOME/dspace-stats-collector directory.
* Installs dspace-stats-collector requeriments and packages in the miniconda python enviroment
* Creates a default configuration file in CURRENT_USER_HOME/dspace-stats-collector/config
* Downloads lastest COUNTER Robots file  
* Installs dspace-stats-collector script in the user crontab 

IMPORTANT: The instalation script and the dspace-stats-collector does not require superuser privileges and don´t install any software outside the CURRENT_USER_HOME/dspace-stats-collector. The collector script execute read only queries over dspace relational db and solr core. This tool doesn´t write or modify any dspace file, dspace db or solr core. It´s recommended, but not mandatory, execute the instalation script from de dspace user. 

Installation steps:

1. Check if wget and cron are installed in the system. 
2. Download installation script from: https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh
3. Execute installation script from a plain user (ie: dspace) 
4. Configure matomo site parameters provided in CURRENT_USER_HOME/dspace-stats-collector/config/default.properties
5. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-collector -v  (will collect and send events for the first time) 
6. Check if the collector is sending data to matomo instance ( do not execute the next step without this check )
7. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-cronify (will install collector in user cron) 
8. Check/ajust the user crontab (the instalation script adds an entry automatically in the user crontab, the collector runs every 60 min by default)   


Credits
-------

This component is part of an alternative DSpace Usage Statistics collector strategy developed by LA Referencia / CONCYTEC (Perú) / IBICT (Brasil) / OpenAIRE as part of OpenAIRE Advance project - WP5 - Subtask 5.2.2. "Pilot common methods for usage statistics across Europe & Latin America"

