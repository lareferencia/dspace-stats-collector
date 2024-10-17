# Manual de Uso del Comando `dspace-stats-export`

### Atención!! Este comando está en fase beta y debe ser utilizado en coordinación con el equipo de LA Referencia a través de su contacto técnico nacional

## Descripción

El comando `dspace-stats-export` se utiliza para ejecutar el colector de estadísticas de DSpace. Este comando procesa eventos y los exporta según los parámetros proporcionados.

## Uso

```sh
CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-export [opciones]
```

`CURRENT_USER_HOME` es el home del usuario que usó para la instalación del collector y donde encontrará el directorio dspace-stats-collector. Los archivos de salida se escribirán en 
`CURRENT_USER_HOME` 

## Opciones

- `--config_dir`: Directorio de configuración (por default toma el mismo directorio que el colector)
- `--verbose`: Activa el modo detallado (verbose).
- `--date_from`: Fecha de inicio en formato `YYYY-MM-DD`.
- `--date_until`: Fecha de fin en formato `YYYY-MM-DD`.
- `--year`: Año para calcular `date_from` y `date_until`.
- `--month`: Mes para calcular `date_from` y `date_until`.
- `--archived_core`: Año del core archivado.

## Ejemplos

### Ejemplo 1: Ejecutar con fechas específicas (menores a un mes)

```sh
CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-export --config_dir=config --date_from=2023-01-10 --date_until=2023-01-20
```

### Ejemplo 2: Ejecutar con año y mes

```sh
CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-export --config_dir=config --year=2023 --month=1
```

## Notas

- Dependiendo de la configuración del SOLR este proceso puede demandar CPU y RAM, por lo que es necesario correrlo en un momento de baja demada de recursos o teniendo en cuenta que podría afectar la estabilidad del sistema. 
- El proceso puede demorar desde minutos hastar horas dependiendo de la cantidad de eventos y las características del servidor donde corre SOLR. 
- Asegúrate de tener los permisos necesarios para crear directorios y archivos en directorio en el que ejecutas el comando
- El periodo entre `date_from` y `date_until` no debe ser mayor a un mes.
- Si no se especifican `date_from` y `date_until`, se deben proporcionar `year` y `month`.

## Archivo de salida

Al finalizar el proceso encontrará un archivo llamada `dspace_stats_export_{YEAR}_{MONTH}.txt.gz` con el año `{YEAR}` y mes `{MONTH}` correspondiente a la fecha parámetro. 

**Este archivo debe ser enviado al equipo central de LA Referencia a través del nodo nacional correspondiente a su repositorio. Por favor coordine previamente el estas acciones con el contacto nacional**


