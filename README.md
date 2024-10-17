LA Referencia DSpace Usage Stats Collector
============================

[![PyPI version](https://img.shields.io/pypi/v/dspace-stats-collector.svg)](https://pypi.python.org/pypi/dspace-stats-collector)

[![License](https://img.shields.io/pypi/l/dspace-stats-collector.svg)](https://pypi.python.org/pypi/dspace-stats-collector)


### ¿Qué es DSpace Stats Collector?

Un agente de Python para enviar eventos de estadísticas de uso de DSpace usando el protocolo Matomo.

Implementación de una alternativa ligera, fácil de desplegar y de solo lectura para un recolector de datos de uso de DSpace compatible con la infraestructura de estadísticas de uso de Matomo (LA Referencia y OpenAIRE). Envía datos de uso de repositorios individuales a un agregador regional externo mediante consultas de solo lectura al subsistema de estadísticas Solr y BD de DSpace.

---
<br/>


## Guías para usuarios LA Referencia 


- [Guía de Instalación (este documento)](https://github.com/lareferencia/dspace-stats-collector/blob/master/README.md)
- [Guía de Actualización](https://github.com/lareferencia/dspace-stats-collector/blob/master/UPDATE.md)
- [Guía de Desinstalación](https://github.com/lareferencia/dspace-stats-collector/blob/master/UNINSTALL.md)
- [Exportador de eventos](https://github.com/lareferencia/dspace-stats-collector/blob/master/EXPORT.md)
---
<br/>
<br/>

# Instalación - Ecosistema LA Referencia

### Requerimientos

- Sistema Operativo basado en Linux
- Realizar la instalación con un usuario distinto de root
- Comprobar que curl  y cron se encuentran instalados en el sistema operativo.
- Poseer instalada una versión de DSpace igual o superior a la 4.x, o DSpace CRIS

## 1. Seleccionar y correr el script de instalación dependiendo de su base de datos 

!!!! Asegúrese de tener instalado curl antes de correr este comando, puede hacerlo ejecutando curl --help y verificando que produzca una salida válida


#### a. Base de datos postgres (estándar)

```
bash <(curl -L -s https://bit.ly/3OL8bNA)
```

#### b. Base de datos Oracle 

```
bash <(curl -L -s https://bit.ly/3feiiOb)
```
El script iniciará descargando e instalando un ambiente Python (https://docs.conda.io/en/latest/miniconda.html) en el directorio home del usuario con que ejecutó el comando anterior.  Este entorno no afecta a ningún paquete base del equipo ni alterará la versión de Python ya instalada. 

**Todo el software instalado corre de manera independiente sin alterar el sistema base.**

Continuará con la instalación de los paquetes Python requeridos.

Finalmente, se instalará el código de la aplicación, se creará el archivo de configuración default (que es preciso reemplazar luego) y se descargará la última versión del archivo COUNTER Robots (utilizado para la identificación de bots.

**Video del proceso:** 
https://www.youtube.com/watch?v=T5Bhf6Ek_u4
 
## 2. Generación del archivo de configuración “default.properties”
 
Ingrese a la dirección http://statsconfig.lareferencia.info/generator.html.   

Verá un formulario con 3 campos obligatorios:

- OpenDOAR ID (*)
- Versión de DSpace instalada, tenga en cuenta que existen opciones para DSpace CRIS y Bases Oracle
- Ruta completa al directorio de instalación de DSpace:  por ejemplo /home/usuario/dspace

ATENCIÓN: En caso de DSPACE CRIS debe ingresar como directorio base el directorio donde reside el código fuente, donde el instalador podrá acceder al build.properties

Luego de hacer **clic en el botón ENVIAR, se descargará automáticamente el archivo default.properties** con los datos específicos para que su repositorio DSpace pueda establecer comunicación con el Matomo de LA Referencia y enviarle estadísticas de uso.

**Reemplace el archivo default.properties que se encuentra en el directorio dspace-stats-collector/config/ por el archivo descargado**

## 3. Ejecución de prueba
 
Seguidamente ejecute el siguiente comando reemplazando **YYYY-MM-DD** por la fecha deseada y **CURRENT_USER_HOME** por el home del usuario que usó para la instalación

El parámetro -f especifica la fecha (año-mes-día) que marca el inicio del envío de datos a Matomo desde el repositorio DSpace. 

**Importante!!: Por favor verifique con su nodo nacional la fecha de inicio de envio para ese momento. No ejecute el comando por primera vez sin esta información.**

```
CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-collector -f YYYY-MM-DD --verbose
```

**Video:** https://www.youtube.com/watch?v=CZeafL52ngg

## 4. Revisión de la bitácora (log de ejecución)
 
Una vez concluida la ejecución, puede revisar el archivo de bitácora creado en CURRENT_USER_HOME/dspace-stats-colector/var/logs/dspace-stats-collector.YYYY-MM-DD.log
 
NOTA: reemplazar **CURRENT_USER_HOME** por el home del usuario que utilizó para ejecutar el comando de instalación.
 
## 5. Verificación de envío a Matomo

Verifique si los datos fueron enviados con éxito al Matomo preguntando al responsable técnico nacional de su nodo. El responsable nacional al ingresar a Matomo debe ingresar al menú Visitantes → Registro de visitas y allí filtrar según la fecha.
 
**Video:** https://www.youtube.com/watch?v=Xn6RGCy93ik
 
**IMPORTANTE!! No ejecute el siguiente paso sin esta verificación).**

## 6. Instalación del cron-job
 
Para instalar la tarea calendarizad (cron-job) que enviará datos automáticamente a Matomo, ejecute:

```
CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-cronify
```

**Video:** https://www.youtube.com/watch?v=OM5HQC5faRU 

NOTA: reemplazar **CURRENT_USER_HOME** por el home del usuario que utilizó para ejecutar el comando de instalación.

**Importante!! Si no realiza esta tarea, el envío periódico no se realizará**

Nota: De acuerdo a las características de su repositorio, puede que sea necesario aumentar la frecuencia de envío de datos.  En caso de tener un repositorio de grandes dimensiones consulte con su técnico responsable del nodo nacional.
 

## 7. Exportación de eventos antiguos

A efectos de facilitar el envío de eventos de meses o años anteriores se ha desarrollado un comando (beta), por favor contacte a su representante nacional para coordinar envíos usando esta herramienta.

[Exportador de eventos](https://github.com/lareferencia/dspace-stats-collector/blob/master/EXPORT.md)


-----------------------------------------------------------------

---------------------------------
------------
-------------
------------

## Legacy - OpenAIRE 2020 

Implementation of a lightweight, easy-to-deploy, read-only alternative for a DSpace usage data collector compatible with Matomo and OpenAire usage statistics infrastructure. It sends usage data from individual repositories to an external regional aggregator by issuing read-only queries to the out-of-the-box DSpace Solr statistics subsystem.

A regional usage statistics service allows the sharing of data on item access across repositories, e-journals and CRIS systems in order to support evaluation, management and reporting. The success of this kind of service depends on installing a collector component in  every repository, so one of the main requirements was to provide a user-friendly, non-invasive and reliable deploying process for repository managers.

This development is part of LA Referencia´s tasks in OpenAIRE Advance project,  aimed to build a pilot on usage data exchange between Latin America and Europe open science infrastructures. 

The design and the development of this usage data collector agent have been based on the following fundamental principles:

* open-source, collaborative development 

* straightforward installation procedure for non-expert Linux users without root or superuser privileges 

* capable of running in a sandbox without the need for installing system-wide packages in the host system

* light-weight and preserving system stability and performance

* fully compatible with OpenAIRE Usage Statistics Service [1]

* adaptable to other software platforms and aggregator services 


Implementation highlights
-------------------------

The solution is based on a “pipe and filter” architecture with input, filter and output stages for events. This approach aims to factorize the problem in independent components, so more stages can be added/connected in the future, allowing to cover other software platforms.

In this first version of the agent, the following  stages have been implemented for DSpace versions 4, 5 and 6, sending events to a Matomo instance, which is analysis platform used by the OpenAIRE [1]:

* DSpace Solr Statistics Input: an initial input component queries the internal DSpace Solr statistics core for new (later than a given/stored timestamp) usage events (item views/ item downloads).  This initial event contains fields for timestamp, item id, user agent, IP address, among others    

* COUNTER Robots Filter: this filter excludes events generated by internet robots and crawlers based on a list of user agent values provided by project COUNTER [3] 

* DSpace Database Filter: this stage queries the internal DSpace relational database (currently only Postgres supported) for complementary item information which is not stored in the Solr core but is required by OpenAire specifications. This filter adds item title, bitstream filename and oai_identifier as event fields

* Matomo API Filter: this filter transforms previously gathered data into the set of parameters required by  Matomo Tracking API [4]

* Matomo Sender Output: this filter buffers and sends batches of events into the regional tracker using the bulk tracking feature of Matomo HTTP Tracking API [4]

.. image::  https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/docs/pipeline-diagram.png

The resulting pipeline runs from the main collector script that stores the last successfully sent timestamp as a state for future calls. 

Credits
-------

This component is part of an alternative DSpace Usage Statistics collector strategy developed by LA Referencia / CONCYTEC (Perú) / IBICT (Brasil) / OpenAIRE as part of OpenAIRE Advance project - WP5 - Subtask 5.2.2. "Pilot common methods for usage statistics across Europe & Latin America"


References
----------

[1] Schirrwagen, Jochen, Pierrakos, Dimitris, MacIntyre, Ross, Needham, Paul, Simeonov, Georgi, Príncipe, Pedro, & Dazy, André. (2017). 

[2] OpenAIRE2020 - Usage Statistics Services - D8.5. doi: https://doi.org/10.5281/zenodo.1034164

[3] Python generators https://wiki.python.org/moin/Generators

[4] Project COUNTER https://www.projectcounter.org/

[5] Matomo tracking API, https://developer.matomo.org/api-reference/tracking-api

[6] DSpace Statistics https://wiki.lyrasis.org/display/DSDOC3x/DSpace+Statistics


