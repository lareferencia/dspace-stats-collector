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

Importante: O script de instalação e o dspace-stats-collector não requerem privilégios de superusuário e não instale os pacot fora da pasta /home/USUARIO/dspace-stats-collector. O script do coletor executa consultas com permissão de “somente leitura” no dspace relational db e solr core. Esta ferramenta não grava ou modifica nenhum arquivo dspace, banco de dados ou solr core. É recomendado, mas na obrigatório, executar a instalação plugin utilizando o usuário dono dos arquivos do DSpace.

Etapas da Instalação:
-------------------



1. Verificar se os programas wget e cron estão instalados no Sistema Operacional. 

2. Baixar o script de instalação pelo endereço, https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh , usando o comando wget. Certifique que está utilizando o usuário padrão(Preferencialmente o proprietário do dspace) e localizado na pasta correta.

  # cd /home/USUARIO/dspace-stats-collector
  
  # wget https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/master/install-standalone.sh

3. Execute o script de instalação utilizando o usuário padrão 

  # sh ./install-standalone.sh

4. Configurar as parametros do matomo no arquivo /home/USUARIO/dspace-stats-collector/config/default.properties, seguindo como exemplo a imagem abaixo. No campo dspace.dir preencher com a localização do diretório do DSpace e no campo dspace.majorVersion preencher com a versão do DSpace. 

 # cd /home/USUARIO/dspace-stats-collector/config
  
 # vim default.properties

EXEMPLO:
 
  matomo.trackerUrl = http://matomo.lareferencia.info/matomo.php

  matomo.idSite = ALTERAR CAMPO PARA INFORMAÇÃO ENVIA POR E-MAIL

  matomo.repositoryId = ALTERAR CAMPO PARA INFORMAÇÃO ENVIA POR E-MAIL

  matomo.token_auth = ALTERAR CAMPO PARA INFORMAÇÃO ENVIA POR E-MAIL

  matomo.rec = 1

  matomo.batchSize = 50
  
  dspace.dir = /dspace
  
  dspace.majorVersion = 6


5. (Primeira execução)Execute o comando /home/USUARIO/dspace-stasts-collector/bin/dspace-stats-collector -v -f AAAA-MM-DD  (os registros enviados serão a partir da data escolhida, no formato AAAA-MM-DD) 

  # /home/USUARIO/dspace-stasts-collector/bin/dspace-stats-collector -v -f AAAA-MM-DD

  EXEMPLO(Registros a partir da data 01/01/2010):
  
  # /home/USUARIO/dspace-stasts-collector/bin/dspace-stats-collector -v -f 2010-01-01

6. Depois de finalizado, check se o plugin enviou os dados para a instancia do Matomo. Não execute os próximos passos caso a etapa acima não tenha sido concluida e todas as informações não tenham sido enviadas.

7. Execute o comando para rodar o comando periodicamente /home/USUARIO/dspace-stasts-collector/bin/dspace-stats-cronify 

  # /home/USUARIO/dspace-stasts-collector/bin/dspace-stats-cronify 

8. Verifique e ajuste a execução do crontab(o script de instalação adiciona uma entrada automaticamente no usuário crontab, o script do será executado periodicamente a cada 60 minutos)   
