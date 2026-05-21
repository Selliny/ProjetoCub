"""Gerenciador de texturas OpenGL."""

from __future__ import annotations

import ctypes
import os
from pathlib import Path

import pygame

from OpenGL.GL import (
    GL_LINEAR,
    GL_LINEAR_MIPMAP_LINEAR,
    GL_REPEAT,
    GL_RGB,
    GL_RGBA,
    GL_TEXTURE_2D,
    GL_TEXTURE_MAG_FILTER,
    GL_TEXTURE_MIN_FILTER,
    GL_TEXTURE_WRAP_S,
    GL_TEXTURE_WRAP_T,
    GL_UNSIGNED_BYTE,
    glBindTexture,
    glGenerateMipmap,
    glTexImage2D,
    glTexParameteri,
)
from OpenGL.raw.GL.VERSION.GL_1_1 import glGenTextures as _glGenTextures

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TextureManager:
    _cache: dict[str, int] = {}  # chave: caminho relativo original

    @classmethod
    def clear_cache(cls) -> None:
        """Limpa IDs OpenGL cacheados quando o contexto grafico e recriado."""
        cls._cache.clear()

    @classmethod
    def load(cls, path: str) -> int:
        """Carrega `path` e retorna o ID OpenGL. Usa cache pelo caminho relativo."""
        if path in cls._cache:
            return cls._cache[path]

        resolved = str(_PROJECT_ROOT / path)
        if not os.path.exists(resolved):
            raise FileNotFoundError(f"Textura não encontrada: {resolved}")

        pygame.display.get_init() or pygame.display.init()
        surf = pygame.image.load(resolved).convert_alpha()
        w, h = surf.get_size()
        has_alpha = surf.get_masks()[3] != 0
        fmt = GL_RGBA if has_alpha else GL_RGB
        data = pygame.image.tostring(surf, "RGBA" if has_alpha else "RGB", True)

        buf = (ctypes.c_uint * 1)()
        _glGenTextures(1, buf)
        tex_id: int = int(buf[0])

        glBindTexture(GL_TEXTURE_2D, tex_id)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, fmt, w, h, 0, fmt, GL_UNSIGNED_BYTE, data)
        glGenerateMipmap(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, 0)

        cls._cache[path] = tex_id  # salva com chave relativa
        return tex_id

    @classmethod
    def bind(cls, tex_id: int) -> None:
        glBindTexture(GL_TEXTURE_2D, tex_id)

    @classmethod
    def unbind(cls) -> None:
        glBindTexture(GL_TEXTURE_2D, 0)
