"""Owners composed by :class:`efm_go.skills.SkillsLoader`.

The loader keeps its state and locks, and the code that repository guards pin to
``skills.py`` by path: the enumerated-read choke point and its readers, the
``repo_scope`` gate sites, trigger scoring, every redactor call site (pending
review and the consent-picker catalog), the tree walk and the packaged-skill sync.
The modules here hold its other rules. A function a loader member delegates to
carries that member's name; a method delegate passes the loader first, and the
function works on the loader's own state, reaches other loader behaviour through
``loader.<method>()`` so a class-level patch still applies, and reads the facade's
constants and its imports from other ``efm_go`` modules through
``efm_go.skills`` at call time.

This package imports nothing on its own: ``efm_go.skills`` imports every
submodule when it loads.
"""
