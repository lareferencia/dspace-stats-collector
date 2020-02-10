.. highlight:: shell

============
INSTALAÇÃO
============

Instalação para usuarios com permissão independente (Pacote python incluso)
-----------------------------------------------------------------

O coletador pode ser executado manualmente ou como uma tarefa agendada usando o sistema de agendamento de tarefas, CRON. Um único script bash de instalação foi desenvolvido para implementar um processo simples de execução. Esse script bash executa as seguintes etapas de instalação e configuração:

* Baixar e instalar um ambiente mínimo de Python (https://docs.conda.io/en/latest/miniconda.html) no diretório origem do usuário;

* Instalar os pacostes Python reinstall necessários; 

* Criar um arquivo de configuração base;

* Baixar o arquivo COUNTER Robots mais recente;

* Oriente o usuário a preencher informações mínimas no arquivo de configuração: o diretório de instalação do DSpace, a versão principal do DSpace e as credenciais necessárias para enviar eventos para uma instância remota do Matomo.

Após esse processo simples de instalação, o coletor está pronto para começar a trabalhar coletando e enviando dados de uso para a instância remota do Matomo pré-configurada. Também é fornecido um comando para instalar o script do coletor no usuário CRONTAB.

Importante: O script de instalação e o dspace-stats-collector não requerem privilégios de superusuário e não instale os pacot fora da pasta /home/NOME_DO_USUARIO/dspace-stats-collector. O script do coletor executa consultas com permissão de “somente leitura” no dspace relational db e solr core. Esta ferramenta não grava ou modifica nenhum arquivo dspace, banco de dados ou solr core. É recomendado, mas na obrigatório, executar a instalação plugin utilizando o usuário dono dos arquivos do DSpace.

Installation steps:
-------------------



1. Verificar se os programas wget e cron estão instalados no Sistema Operacional. 

2. Baixar o script de instalação pelo endereço, https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh , usando o comando wget. Certifique que está utilizando o usuário padrão(Preferencialmente o proprietário do dspace) e localizado na pasta correta.

  # cd CURRENT_USER_HOME
  
  # wget https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh

3. Execute o script de instalação utilizando o usuário padrão



4. Configure matomo site parameters provided in CURRENT_USER_HOME/dspace-stats-collector/config/default.properties

5. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-collector -v -f YYYY-MM-DD  (will collect and send events for the first time from YYYY-MM-DD) 

6. Check if the collector is sending data to matomo instance ( do not execute the next step without this check )

7. Execute CURRENT_USER_HOME/dspace-stasts-collector/bin/dspace-stats-cronify (will install collector in user cron) 

8. Check/ajust the user crontab (the instalation script adds an entry automatically in the user crontab, the collector runs every 60 min by default)   
