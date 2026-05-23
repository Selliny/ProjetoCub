# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 9. Sandboxes — `sandboxes/`

Ambientes de desenvolvimento e teste isolados. Cada sandbox executa de forma independente sem precisar do game loop completo.

### 9.1 `_harness.py` (99 linhas)

Framework OpenGL compartilhado por todos os sandboxes:
- Configura janela pygame, projeção perspectiva, depth test.
- Loop genérico: `draw_fn()`, `on_key()`, `on_frame()`, `setup_camera()`.
- 60 FPS, 10ms de espera mínima.

### 9.2 `sandbox_cube.py` (429 linhas)

**Propósito:** Teste de integração completa Cubo + Mapa + Câmera.  
**Funcionalidades:** Rolamento, state transitions, reações a poderes, câmera orbital, HUD completo, regeneração de mapa com `G`.

### 9.3 `sandbox_block.py` (185 linhas)

**Propósito:** Teste de renderização de um único bloco.  
**Controles:**
- `SPACE`: toggle active
- `P`: alterna tipo de bloco
- `1/2/3`: muda cor
- Câmera orbital para inspeção visual

### 9.4 `sandbox_map.py` (345 linhas)

**Propósito:** Editor visual de grid de blocos.  
**Controles:**
- `WASD`: move cursor no grid
- `ENTER`: adiciona/remove bloco
- `P`: alterna tipo, `1–4`: muda cor, `+/-`: escala
- `SPACE`: toggle active
- `G`: regenera mapa procedural

### 9.5 `sandbox_scene.py` (28 linhas)

**Propósito:** Verificação de renderização do agregador `Scene`. Sem input; apenas verifica que o pipeline funciona.

### 9.6 `menu.py` (468 linhas)

**Propósito:** Menu de seleção de dificuldade e tela de fim de nível.

**Menu principal:**
- Estética retro de terminal com efeito de scanlines CRT.
- Cubo 3D girando em isométrico com decorações ASCII.
- Seleção de dificuldade via setas, mouse ou ENTER.
- Instruções de jogo (WASD, câmera, G).

**Tela de fim:**
- Exibe "PARABÉNS!", vidas restantes, dificuldade atual e próxima.
- ENTER = sair; SPACE = próximo nível (se disponível).

---

## 10. Pipeline de Renderização OpenGL

O projeto usa **Immediate Mode** (glBegin/glEnd) — adequado para fins educacionais.

### 10.1 Configuração (uma vez por contexto)

```
glViewport(0, 0, largura, altura)
glMatrixMode(GL_PROJECTION)
gluPerspective(fov=45°, aspect=W/H, near=0.1, far=100.0)
glMatrixMode(GL_MODELVIEW)
glEnable(GL_DEPTH_TEST)
```

### 10.2 Por Frame

```
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
glLoadIdentity()
gluLookAt(eye, target, up)

# Para cada bloco:
glPushMatrix()
  glTranslatef(x, y, z)
  glScalef(sx, sy, sz)
  glBegin(GL_QUADS)
    glColor3f(r, g, b); glVertex3f(...)  # top
  glEnd()
  glBegin(GL_QUADS)
    glColor3f(r, g, b); glVertex3f(...)  # sides
  glEnd()
glPopMatrix()

# Cubo:
[apply_transform → glTranslatef + glRotatef + glScalef]
glBegin(GL_QUADS); [6 faces] glEnd()
glBegin(GL_LINES); [12 arestas] glEnd()

# HUD (sobreposição 2D):
glMatrixMode(GL_PROJECTION)
glPushMatrix(); glLoadIdentity(); glOrtho(...)
glMatrixMode(GL_MODELVIEW)
glPushMatrix(); glLoadIdentity()
glDrawPixels(...)  # corações e legenda
glPopMatrix(); glMatrixMode(GL_PROJECTION); glPopMatrix()
glMatrixMode(GL_MODELVIEW)

pygame.display.flip()
```

### 10.3 Técnicas Utilizadas

| Técnica | Onde | Propósito |
|---|---|---|
| `glPushMatrix / glPopMatrix` | Blocos, HUD | Isolamento de transforms |
| `glTranslatef + glScalef` | Todos os objetos | Posicionamento e escala |
| `glRotatef` | Cubo (roll, acumulado) | Animação de tombamento |
| `gluLookAt` | Camera | View matrix |
| `gluPerspective` | Setup | Projection matrix |
| `glEnable(GL_BLEND)` | Cubo (fade), overlays | Transparência |
| `glBlendFunc(SRC_ALPHA, ONE_MINUS_SRC_ALPHA)` | Idem | Alpha blending clássico |
| `glDepthFunc(GL_LEQUAL)` | Overlays de blocos | Evitar z-fighting |
| `glTexImage2D` | Texturas | Upload de imagem para GPU |
| `glDrawPixels` | HUD | Texto pygame → pixel buffer |
| `GL_QUADS` | Faces | Geometria principal |
| `GL_LINES` | Arestas do cubo | Wireframe |
| `GL_TRIANGLES` | Símbolos de blocos | Setas, bandeiras |
| `GL_LINE_LOOP` | FragileBlock, SlowBlock | Contornos circulares/poligonais |

---
