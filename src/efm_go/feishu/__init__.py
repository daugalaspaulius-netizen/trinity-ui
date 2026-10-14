"""Feishu (Lark / 飞书) channel.

The package is import-safe WITHOUT the optional ``lark-oapi`` dependency: the
SDK is imported lazily inside :mod:`efm_go.feishu.client` methods, so the
channel roster in :mod:`efm_go.channels` can import ``maybe_start_feishu``
on any build. See ``src/efm_go/docs/feishu-integration.md``.
"""
