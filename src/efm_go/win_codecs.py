"""Guarantee ``utf-8-sig`` on stripped or half-extracted Windows Pythons.

CPython implements ``utf-8`` in C. ``utf-8-sig`` lives in
``encodings/utf_8_sig.py``. A portable SFX that has not finished writing
stdlib, or an interpreter whose ``encodings`` package failed to import,
raises ``LookupError: unknown encoding: utf-8-sig`` the first time a
SKILL.md is read — and the gateway child exits 75 ("Goodbye!").

This module registers a BOM-stripping UTF-8 codec under the usual names
when the stdlib codec is missing. Importing it is enough.
"""
from __future__ import annotations

import codecs

_BOM = b"\xef\xbb\xbf"
_NAMES = frozenset({"utf_8_sig", "utf8_sig", "utf-8-sig", "utf8-sig"})


def _norm(name: str) -> str:
    return name.lower().replace("-", "_")


class _IncrementalDecoder(codecs.BufferedIncrementalDecoder):
    _bom_stripped = False

    def _buffer_decode(self, input, errors, final):  # noqa: N802 - codecs API
        if not self._bom_stripped:
            if input.startswith(_BOM):
                input = input[len(_BOM) :]
                self._bom_stripped = True
            elif len(input) >= len(_BOM) or final:
                self._bom_stripped = True
        return codecs.utf_8_decode(input, errors, final)

    def reset(self) -> None:
        super().reset()
        self._bom_stripped = False


class _IncrementalEncoder(codecs.IncrementalEncoder):
    def __init__(self, errors="strict"):
        super().__init__(errors)
        self._wrote_bom = False

    def encode(self, input, final=False):
        data = codecs.utf_8_encode(input, self.errors)[0]
        if not self._wrote_bom:
            self._wrote_bom = True
            return _BOM + data
        return data

    def reset(self) -> None:
        super().reset()
        self._wrote_bom = False


def _encode(input, errors="strict"):
    return (_BOM + codecs.utf_8_encode(input, errors)[0], len(input))


def _decode(input, errors="strict"):
    if isinstance(input, memoryview):
        input = input.tobytes()
    if input.startswith(_BOM):
        input = input[len(_BOM) :]
    return codecs.utf_8_decode(input, errors, True)


class _StreamWriter(codecs.StreamWriter):
    encode = staticmethod(_encode)


class _StreamReader(codecs.StreamReader):
    decode = staticmethod(_decode)


def _search(name: str):
    key = name.lower()
    if key not in _NAMES and _norm(key) not in {"utf_8_sig", "utf8_sig"}:
        return None
    return codecs.CodecInfo(
        name="utf-8-sig",
        encode=_encode,
        decode=_decode,
        incrementalencoder=_IncrementalEncoder,
        incrementaldecoder=_IncrementalDecoder,
        streamreader=_StreamReader,
        streamwriter=_StreamWriter,
    )


def ensure_utf8_sig() -> None:
    """Register ``utf-8-sig`` when CPython's encodings package does not."""
    try:
        codecs.lookup("utf-8-sig")
        return
    except LookupError:
        pass
    codecs.register(_search)


ensure_utf8_sig()
