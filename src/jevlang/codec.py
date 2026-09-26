"""The ``jev`` source codec.

Python decodes a source file with the codec named in its PEP 263 cookie, so
a file starting with ``# coding: jev`` is handed to us as bytes before the
tokenizer ever sees it.  We decode it as UTF-8, run :func:`transform`, and
give Python back plain Python.  (Same trick as magic_codec.)

The codec has to be registered before such a file is compiled; the
``jevlang.pth`` file installed into site-packages does that at startup.
"""

from __future__ import annotations

import codecs
import encodings

NAME = "jev"


def decode(data, errors: str = "strict") -> tuple[str, int]:
    from .transform import transform

    text = bytes(data).decode("utf-8", errors)
    if text.startswith("﻿"):
        text = text[1:]
    return transform(text), len(data)


def encode(text: str, errors: str = "strict") -> tuple[bytes, int]:
    return text.encode("utf-8", errors), len(text)


class IncrementalDecoder(codecs.BufferedIncrementalDecoder):
    # The transform needs the whole file (match statements look ahead), so
    # buffer everything until the final chunk.
    def _buffer_decode(self, data, errors, final):
        if not final:
            return "", 0
        return decode(data, errors)


class IncrementalEncoder(codecs.IncrementalEncoder):
    def encode(self, text, final=False):
        return text.encode("utf-8", self.errors)


class StreamReader(codecs.StreamReader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._decoder = IncrementalDecoder(self.errors)

    def decode(self, data, errors="strict"):
        # StreamReader feeds chunks; only an empty read signals EOF.
        return self._decoder.decode(data, final=not data), len(data)


class StreamWriter(codecs.StreamWriter):
    def encode(self, text, errors="strict"):
        return encode(text, errors)


def _search(name: str):
    if encodings.normalize_encoding(name).lower() != NAME:
        return None
    return codecs.CodecInfo(
        name=NAME,
        encode=encode,
        decode=decode,
        incrementalencoder=IncrementalEncoder,
        incrementaldecoder=IncrementalDecoder,
        streamreader=StreamReader,
        streamwriter=StreamWriter,
    )


_registered = False


def register() -> None:
    global _registered
    if not _registered:
        codecs.register(_search)
        _registered = True
