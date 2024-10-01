# Desinstalación del DSpace Usage Stats Collector

Si resulta necesario remover completamente el Dspace Usage Stats Collector los pasos son los siguientes:
 
## 1. Borrar directorio dspace-stats-collector

En el directorio home del usuario utilizado para la instalación de la versión anterior, se encuentra el directorio **dspace-stats-collector**.  

**Este debe ser totalmente removido antes de proceder con una nueva instalación.**
 
## 2. Borrar archivos relacionados en directorio “home”

Dependiendo de la versión instalada es posible que en el directorio home del usuario utilizado para instalar el software recolector, se encuentren los siguientes archivos:

- requirements.txt
- install-standalone.sh
- Miniconda3-latest-Linux-x86_64.sh

**Todos ellos deben ser borrados antes de proceder con una nueva instalación.**
 
## 3. Desactivar el envío automático de datos estadísticos

La versión anterior de DSpace Usage Stats Collector calendarizó el envío automático de datos cada hora.  Esta instrucción debe eliminarse de los trabajos calendarizados específicos del usuario con el que se realizó la instalación.  Con el comando:

```
crontab -e [username]
````

observará los trabajos calendarizados (cronjobs), **busque y borre el que posee algo similar a:** 

```
*/59 * * * * /home/username/dspace-stats-collector/bin/dspace-stats-collector
````

**Seguidamente guarde y cierre el archivo.**