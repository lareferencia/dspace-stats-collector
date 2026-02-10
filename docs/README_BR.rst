.. highlight:: shell

============
INSTALACAO
============

Instalacao standalone em nivel de usuario (Linux)
-------------------------------------------------

O coletor pode ser executado manualmente ou via CRON.
O instalador atual e autocontido e instala tudo em ``/home/USUARIO/dspace-stats-collector`` sem privilegios de root.

Requisitos base
---------------

* Linux
* Usuario sem root
* ``curl``, ``git``, ``tar``, ``gzip``, ``grep``, ``sed``, ``awk``, ``sort``, ``tail``, ``mktemp``, ``uname``
* ``cron`` disponivel no sistema
* DSpace 4+ / 5+ / 6+ / CRIS
* Opcional: Python 3.10+ no sistema (se nao existir, o instalador usa Miniconda local)

Passos de instalacao
--------------------

1. Execute diretamente do GitHub:

   ``bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)``

2. Selecione a referencia de versao.
   O padrao e a maior versao encontrada em tags/branches no formato ``vX.Y`` ou ``vX.Y.Z``.

3. O modo development (editable) e opcional.
   O modo stable e o padrao.

Comportamento de runtime e compatibilidade
------------------------------------------

* Stable (``v1.x`` e superior) usa perfil Python 3.10+.
* Legacy (``v0.x``) usa perfil Python 3.8.
* Stable e somente PostgreSQL (Oracle nao incluido).
* Se existir Python compativel no sistema, usa ``venv``.
* Se nao existir, instala Miniconda local.
* Em ambos os casos os caminhos permanecem compativeis:

  * ``/home/USUARIO/dspace-stats-collector/bin``
  * ``/home/USUARIO/dspace-stats-collector/config``

* Em reinstalacao/atualizacao, ``config`` e ``var/state`` sao preservados automaticamente.

Passos apos instalacao
----------------------

1. Substitua ``/home/USUARIO/dspace-stats-collector/config/default.properties`` pelo arquivo especifico do repositorio.

2. Execute teste inicial:

   ``/home/USUARIO/dspace-stats-collector/bin/dspace-stats-collector -f AAAA-MM-DD --verbose -c /home/USUARIO/dspace-stats-collector/config``

3. Confirme com o gestor do nodo nacional que os dados chegaram ao Matomo.

4. Ative execucao periodica:

   ``/home/USUARIO/dspace-stats-collector/bin/dspace-stats-cronify -c /home/USUARIO/dspace-stats-collector/config``
