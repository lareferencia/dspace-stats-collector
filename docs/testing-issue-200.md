# Validación de la corrección del issue #200 — versión 1.0.1

Issue: https://github.com/lareferencia/lareferencia-helpdesk/issues/200

## Qué cambia

Antes, el cursor buscaba en ventanas diarias y abandonaba tras unos 30 días sin
eventos. Como no se había enviado ningún evento, el timestamp persistido seguía
igual y las siguientes ejecuciones repetían la misma búsqueda.

Ahora consulta desde el último timestamp hasta un límite superior fijo: el
instante UTC al comenzar la lectura, o `--date_until` si se proporciona. Solr
entrega los primeros eventos ordenados por fecha aunque haya meses o años vacíos.
Se mantienen el tamaño de página y el límite total de eventos. Al alcanzar el
límite no se realiza una consulta adicional con cero filas.

Una respuesta vacía termina la lectura y no modifica el estado. El sender de
Matomo sigue siendo responsable de guardar el último timestamp confirmado; un
fallo de conexión deja los eventos pendientes para la siguiente ejecución.
El parámetro interno `maxDaysToLookForEvents` se conserva por compatibilidad,
pero deja de limitar la búsqueda. La versión del paquete pasa de 1.0.0 a 1.0.1
(también se actualiza la configuración de bumpversion).

## Preparación

Usar una instalación y un sitio Matomo de pruebas. Conservar una copia de
`~/dspace-stats-collector/var/timestamp/default.dat` y de la configuración antes
de empezar. Los envíos históricos a un sitio real pueden duplicar estadísticas.
Los eventos de prueba deben cumplir los filtros de Solr y tener recursos válidos
en la base de datos de DSpace.

Instalar esta rama en un entorno Python 3.10+ con las dependencias del perfil
`installer/requirements/stable-py310.txt` y el paquete en modo editable:

```bash
python -m pip install -r installer/requirements/stable-py310.txt
python -m pip install -e . pytest
python -c 'from dspace_stats_collector import __version__; print(__version__)'
python -m pytest -q tests/test_solr_gaps.py tests/test_matomo_sender.py tests/test_pipeline_errors.py tests/test_setup_metadata.py
```

La versión mostrada debe ser `1.0.1`.

## Casos manuales y resultados esperados

1. **Hueco mayor de 30 días:** partir de un timestamp seguido por varios meses
   sin eventos y después eventos válidos en el mismo core. Ejecutar el colector
   con `--verbose`. Debe encontrar y enviar esos eventos en esa ejecución, sin
   editar manualmente el archivo de estado. Repetir con un hueco entre páginas.
2. **Rango completamente vacío:** ejecutar sobre un intervalo sin coincidencias.
   Debe terminar normalmente, sin enviar ni adelantar el timestamp. Una ejecución
   posterior debe poder encontrar eventos que aparezcan después del checkpoint.
3. **Matomo inaccesible:** anotar el checkpoint, apuntar al endpoint de pruebas
   inaccesible y ejecutar con eventos posteriores a un hueco largo. No debe
   guardarse como enviado el lote fallido. Restablecer Matomo y ejecutar de nuevo
   sin `-f`; debe recuperar y enviar los eventos pendientes. Si hubo lotes
   confirmados antes del fallo, debe reanudar desde el último lote confirmado.
4. **Timeout de Matomo:** simular un timeout en el endpoint de pruebas. Deben
   mantenerse los tres intentos con espera exponencial y conservarse el checkpoint
   anterior al lote si se agotan los intentos.
5. **Límites:** configurar `max.eventsToSend` bajo y comprobar que lo respeta y
   que la siguiente ejecución continúa. Usar `--date_until` y comprobar que no
   se incluyen eventos posteriores a ese límite (el extremo superior es inclusivo).
6. **Core anual:** si los eventos están archivados, seleccionar el core correcto
   con `--archived_core YYYY`. La corrección busca dentro del core seleccionado;
   no descubre ni combina automáticamente cores anuales.

Comparar identificadores y timestamps de los eventos esperados en Solr con los
recibidos por Matomo, además del archivo de estado y el log. Registrar versión
DSpace/Solr, configuración de límites, duración y resultado de cada caso.

## Alcance de la validación

Las pruebas automatizadas usan Solr y HTTP simulados. Se requiere testing con
servicios reales, especialmente del coste de consultas sobre intervalos amplios.
La paginación por timestamp y los filtros/enriquecimiento existentes no cambian;
esta corrección no añade un cursor compuesto para eventos con idéntico timestamp
ni garantiza entrega exactamente una vez ante respuestas HTTP perdidas.
