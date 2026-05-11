# Exportación de eventos históricos

El comando `dspace-stats-export` permite generar un archivo comprimido con eventos históricos de uso en el mismo formato de solicitudes Matomo que produce el colector.

Este flujo está pensado para cargas históricas, reprocesamientos puntuales o envíos coordinados con LA Referencia. No debe usarse como reemplazo del envío periódico normal con `dspace-stats-collector` y cron.

## Uso coordinado

En despliegues LA Referencia, coordine siempre el uso de este comando con el responsable técnico de su nodo nacional antes de generar o enviar archivos históricos.

El archivo resultante debe enviarse al equipo central de LA Referencia a través del nodo nacional correspondiente.

## Requisitos previos

- Tener instalado DSpace Stats Collector.
- Contar con un `default.properties` válido en el directorio de configuración.
- Ejecutar el comando con acceso de lectura al Solr de estadísticas y a la base de datos DSpace.
- Ejecutarlo en un momento de baja carga si el periodo contiene muchos eventos.
- Elegir el directorio de trabajo donde se quiere crear el archivo `.gz`.

## Uso básico

```bash
~/dspace-stats-collector/bin/dspace-stats-export [opciones]
```

Por defecto, el comando usa:

```text
~/dspace-stats-collector/config
```

como directorio de configuración.

Si desea usar otro directorio de configuración, indique `-c` o `--config_dir`:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -c ~/dspace-stats-collector/config [opciones]
```

## Selección del periodo

Debe elegir una de estas dos formas de indicar el periodo a exportar.

### Exportar un mes completo

Use `--year` y `--month`, o sus formas cortas `-y` y `-m`:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y 2023 -m 1
```

Este ejemplo exporta enero de 2023 completo.

### Exportar un rango de fechas

Use `--date_from` y `--date_until`, o sus formas cortas `-f` y `-u`:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -f 2023-01-10 -u 2023-01-20
```

El formato de ambas fechas es `YYYY-MM-DD`.

El comando procesa desde el inicio de `date_from` hasta el final del día indicado en `date_until`.

El periodo total no debe superar 31 días.

## Opciones

- `-c`, `--config_dir`: directorio de configuración. Por defecto usa `~/dspace-stats-collector/config`.
- `-v`, `--verbose`: activa salida detallada.
- `-f`, `--date_from`: fecha inicial del rango, en formato `YYYY-MM-DD`.
- `-u`, `--date_until`: fecha final del rango, en formato `YYYY-MM-DD`.
- `-y`, `--year`: año que se quiere exportar cuando se usa modo mensual.
- `-m`, `--month`: mes que se quiere exportar cuando se usa modo mensual.
- `-a`, `--archived_core`: año del core Solr archivado, cuando el repositorio usa cores de estadísticas separados por año.

## Cores Solr archivados

Si su DSpace mantiene estadísticas históricas en un core Solr separado, puede usar `--archived_core`.

Por ejemplo:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y 2022 -m 12 -a 2022
```

Con la configuración default, esta opción hace que el colector consulte un core con sufijo de año, por ejemplo `statistics-2022`.

Use esta opción solo si su instalación DSpace realmente usa cores archivados con ese nombre.

## Archivo de salida

El archivo se crea en el directorio desde donde se ejecuta el comando.

El nombre tiene este formato:

```text
dspace_stats_export_<idSite>_<YYYY>_<MM>.txt.gz
```

Por ejemplo:

```text
dspace_stats_export_12_2023_01.txt.gz
```

Cada línea del archivo contiene una solicitud Matomo generada por el pipeline de exportación. Los eventos identificados como robots no se escriben en el archivo final.

## Recomendaciones operativas

- Ejecute la exportación en horarios de baja carga.
- Exporte periodos pequeños y repita el proceso por mes si necesita cubrir rangos largos.
- Revise la salida del comando y confirme que se generó el archivo esperado.
- Coordine el envío del archivo antes de compartirlo con LA Referencia.
- Conserve una copia local hasta que el nodo nacional confirme la recepción y procesamiento.

## Ejemplos

Exportar un mes completo usando la configuración default:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y 2023 -m 1
```

Exportar un rango de fechas usando configuración explícita:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -c ~/dspace-stats-collector/config -f 2023-01-10 -u 2023-01-20
```

Exportar desde un core archivado:

```bash
~/dspace-stats-collector/bin/dspace-stats-export -y 2022 -m 12 -a 2022
```

## Relación con el colector periódico

`dspace-stats-export` genera un archivo local para revisión o envío coordinado. No envía eventos directamente a Matomo.

Para el envío periódico normal, use:

```bash
~/dspace-stats-collector/bin/dspace-stats-collector
```

y active el cron con:

```bash
~/dspace-stats-collector/bin/dspace-stats-cronify
```
