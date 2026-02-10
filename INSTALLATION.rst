.. highlight:: shell

============
Installation
============

Standalone user-level installation (Linux)
------------------------------------------

The collector can run manually or as a scheduled CRON task.
The current installer is self-contained and installs everything under
``CURRENT_USER_HOME/dspace-stats-collector`` without root privileges.

Base requirements
-----------------

* Linux
* Non-root user account
* ``curl``, ``git``, ``tar``, ``gzip``, ``grep``, ``sed``, ``awk``, ``sort``, ``tail``, ``mktemp``, ``uname``
* ``cron`` available in the host system
* DSpace 4+ / 5+ / 6+ / CRIS
* Optional: Python 3.10+ in system (if missing, installer falls back to local Miniconda)

Install steps
-------------

1. Run installer directly from GitHub:

   ``bash <(curl -fsSL https://raw.githubusercontent.com/lareferencia/dspace-stats-collector/main/installer/install.sh)``

2. Choose release ref (default is the highest versioned tag/branch in ``vX.Y`` or ``vX.Y.Z`` format), or press Enter.

3. Choose development mode only if you need editable branch installation.
   Stable mode is the default.

Runtime and compatibility behavior
----------------------------------

* Stable refs (``v1.x`` and newer) require Python 3.10+ profile.
* Legacy refs (``v0.x``) use Python 3.8 profile.
* Stable profile is PostgreSQL-only (Oracle is not included).
* If compatible system Python exists, installer uses ``venv``.
* If compatible Python is not available, installer installs local Miniconda.
* In both cases, command and config paths stay compatible with previous deployments:

  * ``CURRENT_USER_HOME/dspace-stats-collector/bin``
  * ``CURRENT_USER_HOME/dspace-stats-collector/config``

* During reinstall/update, previous ``config`` and ``var/state`` are backed up and restored automatically.

Post-install steps
------------------

1. Replace ``CURRENT_USER_HOME/dspace-stats-collector/config/default.properties`` with your repository-specific file.

2. Execute first collection test:

   ``CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-collector -f YYYY-MM-DD --verbose -c CURRENT_USER_HOME/dspace-stats-collector/config``

3. Check with your national node manager that data is arriving in Matomo before enabling cron.

4. Install scheduled execution:

   ``CURRENT_USER_HOME/dspace-stats-collector/bin/dspace-stats-cronify -c CURRENT_USER_HOME/dspace-stats-collector/config``

Update
------

Run the same installer command again using the same system user used in the original installation.
See ``UPDATE.md`` for non-interactive examples.
