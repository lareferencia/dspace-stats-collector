# Guia de instalacion para LA Referencia

Esta guia esta dirigida a repositorios DSpace que reportan estadisticas de uso al ecosistema LA Referencia. Para una introduccion general al proyecto y una instalacion no especifica de LA Referencia, consulte [README.md](README.md).

## Proposito

DSpace Stats Collector envia eventos de uso de un repositorio DSpace hacia Matomo mediante consultas de solo lectura al nucleo de estadisticas Solr y a la base de datos del repositorio.

En despliegues LA Referencia, la instalacion debe coordinarse con el nodo nacional correspondiente, especialmente para definir la fecha inicial de envio y validar que los eventos lleguen correctamente a Matomo antes de activar el cron.

## Requisitos

- Sistema operativo basado en Linux.
- Instalacion y ejecucion con un usuario distinto de `root`.
- `curl`, `git` y `cron` disponibles en el sistema operativo.
- DSpace 4 o superior, o DSpace CRIS compatible.
- PostgreSQL para el perfil stable actual. Oracle queda como esquema legacy y no esta incluido en el perfil stable del instalador.
- Coordinacion con el responsable tecnico nacional de LA Referencia.

## Instalacion autocontenida

Ejecute el instalador desde el usuario final de operacion:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)
```

El instalador deja la estructura compatible con despliegues previos en:

- `~/dspace-stats-collector/bin`
- `~/dspace-stats-collector/config`

Segun la disponibilidad del sistema, usara `venv` con Python 3.10 o superior, o instalara un Miniconda local como fallback sin modificar el Python global del sistema.

Mas opciones del instalador estan documentadas en [installer/README.md](installer/README.md).

## Generacion de `default.properties`

Ingrese al generador de configuracion:

```text
http://statsconfig.lareferencia.info/generator.html
```

El formulario solicita tres campos obligatorios:

- OpenDOAR ID.
- Version de DSpace instalada.
- Ruta completa al directorio de instalacion de DSpace, por ejemplo `/home/usuario/dspace`.

En instalaciones DSpace CRIS, indique como directorio base el directorio donde reside el codigo fuente y donde el instalador puede acceder a `build.properties`.

Al enviar el formulario, se descargara automaticamente un archivo `default.properties` con los datos necesarios para comunicar el repositorio con el Matomo de LA Referencia.

## Reemplazo de configuracion

Reemplace el archivo generado por el instalador:

```text
~/dspace-stats-collector/config/default.properties
```

por el archivo `default.properties` descargado desde el generador de LA Referencia.

## Primera ejecucion supervisada

Antes de ejecutar por primera vez, verifique con su nodo nacional la fecha inicial de envio que corresponde a su repositorio.

No ejecute el colector por primera vez sin esta confirmacion.

Use el parametro `-f` para indicar la fecha inicial:

```bash
~/dspace-stats-collector/bin/dspace-stats-collector -f YYYY-MM-DD --verbose
```

Reemplace `YYYY-MM-DD` por la fecha acordada con su nodo nacional.

## Revision de logs

Al finalizar la ejecucion, revise la bitacora generada en:

```text
~/dspace-stats-collector/var/logs/dspace-stats-collector.YYYY-MM-DD.log
```

Si la ejecucion no usa una fecha explicita, el log general se crea en:

```text
~/dspace-stats-collector/var/logs/dspace-stats-collector.log
```

## Verificacion en Matomo

Luego de la primera ejecucion, confirme con el responsable tecnico nacional que los eventos fueron recibidos correctamente en Matomo.

La validacion debe realizarse antes de instalar el cron. El responsable nacional puede revisar Matomo en el menu de visitantes y filtrar por la fecha procesada.

## Instalacion del cron

Instale la tarea programada solo despues de confirmar que el envio manual fue exitoso:

```bash
~/dspace-stats-collector/bin/dspace-stats-cronify
```

Si no se instala esta tarea, el envio periodico no se realizara.

En repositorios de gran volumen puede ser necesario aumentar la frecuencia de envio. Coordine este ajuste con el responsable tecnico del nodo nacional.

## Exportacion de eventos antiguos

Para enviar eventos de meses o anos anteriores existe el comando de exportacion, actualmente orientado a flujos coordinados con LA Referencia.

El comando genera un archivo comprimido local, no envia los eventos directamente a Matomo:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y YYYY -m M
```

Consulte la guia completa en [EXPORT.md](EXPORT.md) y coordine previamente cualquier envio historico con su contacto tecnico nacional.

## Actualizacion y desinstalacion

- Para actualizar una instalacion existente, ejecute nuevamente el instalador con el mismo usuario de operacion. Las opciones avanzadas estan en [installer/README.md](installer/README.md).
- Para remover una instalacion, consulte [UNINSTALL.md](UNINSTALL.md).
