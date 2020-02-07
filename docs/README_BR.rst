.. highlight:: shell

============
INSTALAÇÃO
============

Instalação para usuarios com permissão independente (Pacote python incluso)
-----------------------------------------------------------------

O coletador pode ser executado manualmente ou como uma tarefa agendada usando o sistema de agendamento de tarefas, CRON. Um único script bash de instalação foi desenvolvido para implementar um processo simples de execução. Esse script bash executa as seguintes etapas de instalação e configuração:

* download and install a free minimal Python environment (https://docs.conda.io/en/latest/miniconda.html) in the user home directory

* install required Python packages 

* create the default configuration file 

* download the latest COUNTER Robots file

* instruct the user to fill minimal information in the configuration file: the DSpace installation directory, the DSpace major version and the required credentials for sending events to a remote Matomo instance

After this simple installation process, the collector is ready to start working by collecting and sending usage data into the pre-configured remote Matomo instance. Also a command to install the collector script in the user CRONTAB is provided. 

IMPORTANT: The instalation script and the dspace-stats-collector does not require superuser privileges and don´t install any software outside the CURRENT_USER_HOME/dspace-stats-collector. The collector script execute read only queries over dspace relational db and solr core. This tool doesn´t write or modify any dspace file, dspace db or solr core. It´s recommended, but not mandatory, execute the instalation script from de dspace user. 

Installation steps:
-------------------



1. Verificar se os programas wget e cron estão instalados no Sistema Operacional. 

2. Baixar o script de instalação pelo endereço, https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh , usando o comando wget. Certifique que está utilizando o usuário padrão(Preferencialmente o proprietário do dspace) e localizado na pasta correta.

  # cd /home/NOME_USUARIO/dspace-stats-collector
  
  # wget https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh

3. Execute o script de instalação utilizando o usuário padrão( ) 

4. Configure matomo site parameters provided in CURRENT_USER_HOME/dspace-stats-collector/config/default.properties

5. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-collector -v -f YYYY-MM-DD  (will collect and send events for the first time from YYYY-MM-DD) 

6. Check if the collector is sending data to matomo instance ( do not execute the next step without this check )

7. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-cronify (will install collector in user cron) 

8. Check/ajust the user crontab (the instalation script adds an entry automatically in the user crontab, the collector runs every 60 min by default)   
