"""The report sections of ``kirocrew doctor``, one module per family.

:mod:`efm_go.cli_doctor` is the command's facade and orchestrator: it prints the
sections in a fixed order, owns the rows repository gates pin to that file, and
renders the verdict and exit code. The families here hold the rest:

* :mod:`~efm_go.doctor_checks.render` -- the escaping, indent and wrapping
  helpers the sections share
* :mod:`~efm_go.doctor_checks.agents` -- Crew members, deprecated agent specs, the
  optional Claude Code backend row and the per-harness sign-in rows
* :mod:`~efm_go.doctor_checks.mcp` -- strict-identity routing, the MCP gateway
  daemon, and each harness's MCP projection
* :mod:`~efm_go.doctor_checks.confinement` -- the sandbox backend verdict and the
  shapes that make the launcher refuse a spawn
* :mod:`~efm_go.doctor_checks.access` -- session signing, hook auto-approve and the
  credential posture an agent sees
* :mod:`~efm_go.doctor_checks.install` -- the project directory, data home, launcher,
  deployed skill content, source checkout and Python runtime
* :mod:`~efm_go.doctor_checks.services` -- the service definition, its environment,
  the pod session bus, the dashboard's bind and auth, and whether the gateway answers
* :mod:`~efm_go.doctor_checks.resources` -- memory pressure, tmpfs headroom,
  installer residue and the agents directory
* :mod:`~efm_go.doctor_checks.workload` -- cron health, the task queue, overload
  bounds and loop-stall history
* :mod:`~efm_go.doctor_checks.channels` -- Slack, Discord, WhatsApp and every other
  channel
* :mod:`~efm_go.doctor_checks.features` -- vector memory and speech-to-text

The orchestrator imports these when a health report runs (``--bundle`` prints no
report and imports none of them), so ``import efm_go.cli`` never pays for them.
Because a family loads on that first use, it binds no project module by name but the
facade and its sibling families: it reads every other one through the facade at call
time (``cli_doctor.sandbox``), so the moment it loads cannot capture a module a test
has rebound, and a patch of the facade's binding reaches it.
"""
