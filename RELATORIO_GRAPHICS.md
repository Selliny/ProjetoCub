# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 3. Módulo `src/graphics/`

Contém primitivas de computação gráfica **independentes do jogo**. Não têm lógica de gameplay — apenas encapsulam estados gráficos e chamadas OpenGL.

### 3.1 `Color` — `src/graphics/color.py`

Encapsulamento de uma cor RGBA normalizada.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `r` | `float` | Canal vermelho [0.0, 1.0] |
| `g` | `float` | Canal verde [0.0, 1.0] |
| `b` | `float` | Canal azul [0.0, 1.0] |
| `a` | `float` | Canal alfa [0.0, 1.0], padrão 1.0 |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `__init__` | `(r, g, b, a=1.0)` | Constrói a cor |
| `apply` | `() → None` | Chama `glColor4f(r, g, b, a)` |

---

### 3.2 `Position` — `src/graphics/position.py`

Vetor 3D representando uma posição no espaço.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `x` | `float` | Coordenada horizontal |
| `y` | `float` | Coordenada vertical (altura) |
| `z` | `float` | Coordenada de profundidade |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `__init__` | `(x=0.0, y=0.0, z=0.0)` | Constrói a posição |
| `translate` | `(dx, dy, dz) → None` | Incrementa cada eixo |
| `apply` | `() → None` | Chama `glTranslatef(x, y, z)` |

---

### 3.3 `Size` — `src/graphics/size.py`

Fatores de escala independentes por eixo.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `sx` | `float` | Escala no eixo X |
| `sy` | `float` | Escala no eixo Y |
| `sz` | `float` | Escala no eixo Z |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `__init__` | `(sx=1.0, sy=1.0, sz=1.0)` | Constrói com escalas individuais |
| `uniform` | `classmethod(factor) → Size` | Cria `Size(f, f, f)` |
| `apply` | `() → None` | Chama `glScalef(sx, sy, sz)` |

**Uso no jogo:** O cubo usa `Size.uniform(0.5)` ao receber o poder **Shrink** e `Size.uniform(1.0)` ao receber **Grow**.

---

### 3.4 `Camera` — `src/graphics/camera.py`

Câmera 3D com modelo esférico (yaw/pitch). Disponível como componente, mas o `main.py` implementa sua própria câmera orbital diretamente.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `eye_x, eye_y, eye_z` | `float` | Posição da câmera no mundo |
| `yaw` | `float` | Rotação horizontal em graus (padrão 180°) |
| `pitch` | `float` | Elevação em graus; clampado ±89° |
| `zoom` | `float` | Fator de escala externo [0.3, 4.0] |
| `tilt` | `float` | Achatamento vertical [0.2, 1.0] |

**Constantes:**

| Constante | Valor | Descrição |
|---|---|---|
| `MOVE_STEP` | `0.3` | Unidades por tecla pressionada |
| `MOUSE_SENSITIVITY` | `0.3` | Graus por pixel do mouse |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `move_forward` | `(d) → None` | Avança/recua ao longo do yaw (horizontal) |
| `strafe` | `(d) → None` | Desloca lateral, perpendicular ao yaw |
| `rotate` | `(dyaw, dpitch) → None` | Rotaciona; clamp pitch ±89° |
| `handle_scroll` | `(event) → None` | Ajusta zoom via `MOUSEWHEEL` |
| `update_keys` | `(keys) → None` | WASD/setas=mover, Q/E=yaw, R/F=tilt |
| `apply` | `() → None` | Aplica `gluLookAt()` na matriz MODELVIEW |

---

### 3.5 `TextureManager` — `src/graphics/texture.py`

Gerenciador estático de texturas OpenGL com cache por caminho relativo.

**Estado Interno (classe):**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_cache` | `dict[str, int]` | `{caminho_relativo: tex_id}` |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `load` | `classmethod(path) → int` | Carrega e cacheia textura; retorna ID OpenGL |
| `clear_cache` | `classmethod() → None` | Limpa o cache (chamado na troca de contexto) |

**Fluxo de carregamento:**
1. Verifica cache; se presente, retorna ID salvo.
2. Abre imagem com `pygame.image.load()`.
3. Converte para RGBA e obtém raw bytes.
4. Chama `glGenTextures`, `glBindTexture`, `glTexImage2D`, parâmetros de filtro.
5. Armazena e retorna o ID.

**Nota:** Cada subclasse de `Block` mantém seu próprio `_tex_id: int | None = None` e usa `_get_tex()` para acesso lazy. O método `Block.reset_texture_cache()` limpa recursivamente todos os `_tex_id` das subclasses.

---
