"""The cron service's owners, composed by :class:`efm_go.cron.CronService`.

Each module owns one responsibility and, at import time, imports only modules
listed above it:

* :mod:`~efm_go.cron_service.schedule` -- when a job fires (next run, due, jitter,
  rendering, time parsing);
* :mod:`~efm_go.cron_service.model` -- the job record itself;
* :mod:`~efm_go.cron_service.identity` -- the session key a run presents, the
  principal it names, the memory it runs with;
* :mod:`~efm_go.cron_service.claims` -- a run's occupancy of its job;
* :mod:`~efm_go.cron_service.execution` -- a run's deadlines and terminal record;
* :mod:`~efm_go.cron_service.store` -- ``crons.json``'s format, lock and failure types;
* :mod:`~efm_go.cron_service.fields` -- what a valid job and a valid update are;
* :mod:`~efm_go.cron_service.readers` -- read-only views of the store with no
  scheduler running;
* :mod:`~efm_go.cron_service.folders` -- cron folder definitions.

:mod:`efm_go.cron` stays the import and patch surface: every name these modules
hold is re-exported there as the same object, and a name tests patch there is read
by these modules through it on each call (a function-local import, so the module
graph stays acyclic at import time).
"""
