# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 7. Módulo `src/input/`

### `InputHandler` — `src/input/handler.py` (27 linhas)

Mapeia eventos de teclado do pygame para chamadas de `try_roll` no cubo.

**Mapeamento:**

| Tecla | `(dx, dz)` |
|---|---|
| `K_LEFT` | `(-1, 0)` |
| `K_RIGHT` | `(1, 0)` |
| `K_UP` | `(0, -1)` |
| `K_DOWN` | `(0, 1)` |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `handle` | `(event, scene) → None` | Despacha KEYDOWN para `scene.cube.try_roll()` |

> **Nota:** Supersedido em grande parte pelo polling direto de `pygame.key.get_pressed()` no `main.py`.

---

## 8. Ponto de Entrada — `main.py` (467 linhas)

Orquestra todo o jogo: menu, inicialização, game loop, câmera orbital, HUD e progressão de dificuldade.

### 8.1 Inicialização

1. **Menu** (`run_menu()`): Tela retro com cubo girando e seleção de dificuldade. Retorna `DifficultyConfig`.
2. **pygame + OpenGL**: `pygame.init()`, `pygame.display.set_mode()`, `glViewport`, `gluPerspective(45°)`, `glEnable(GL_DEPTH_TEST)`.
3. **Geração do mapa**: `Map.generate(**config)`.
4. **Spawn do cubo**: `Cube(position=Position(start_x, 0.5, start_z))`.
5. **Câmera**: `camera_yaw = 0`, `camera_distance = 12`, `camera_height = 8`.

### 8.2 Game Loop (60 FPS)

**Processamento de eventos:**
- `ESC` / `QUIT` → sair
- `G` → regenerar mapa com mesma dificuldade
- Mouse drag → ajusta `camera_yaw` e `camera_height`

**Update:**
```python
map_.update(dt)            # Timers de FragileBlock
cube.update(dt)            # State machine + animações
# Verificar win: cube.reached_end && state==IDLE → próxima dificuldade
# Verificar death: cube.is_dead && state==IDLE → resetar
```

**Input do cubo (somente quando não está se movendo):**
- `W` / `Up arrow` → `try_roll(0, -1, map_)` — mas se `controls_inverted`, inverte para `(0, 1)`
- `S` / `Down arrow` → `try_roll(0, 1, map_)`
- `A` → `try_roll(-1, 0, map_)`
- `D` → `try_roll(1, 0, map_)`

**Câmera orbital com suavização:**
```python
desired_eye = cube_pos + rotate(yaw) * distance + height
camera_eye = lerp(camera_eye, desired_eye, 8.0 * dt)
camera_target = lerp(camera_target, cube_pos, 8.0 * dt)
```

**Render:**
```python
glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
glClearColor(0.2, 0.5, 0.8, 1.0)   # Fundo azul céu
gluLookAt(eye, target, up=(0,1,0))
map_.draw()
cube.apply_transform(); cube.draw()
_draw_hud(lives, max_lives)
pygame.display.flip()
```

### 8.3 HUD (`_draw_hud`)

Renderizado em sobreposição 2D (projeção ortogonal) sobre a cena 3D:

1. Salva estado da matriz; troca para `GL_PROJECTION` + `glOrtho(0, W, 0, H)`.
2. **Corações**: fileira no canto superior esquerdo.
   - Cheios (vermelho) para vidas ativas; vazios (cinza) para max_lives.
   - Renderizados como superfícies pygame, convertidas para bytes e enviadas via `glDrawPixels`.
3. **Legenda de poderes**: abaixo dos corações.
   - 10 entradas: quadrado colorido + rótulo em Consolas 15pt.
   - Mesmo pipeline `glDrawPixels`.
4. Restaura projeção perspectiva original.

### 8.4 Sistema de Dificuldade e Progressão

`DifficultyConfig` (dataclass em `sandboxes/menu.py`) com 31 campos:

| Campo | Tipo | Descrição |
|---|---|---|
| `label` | `str` | Nome legível ("Fácil", "Médio", "Difícil") |
| `challenge_profile` | `str` | Perfil de zona ("easy", "medium", "hard") |
| `generator` | `str` | "loop" ou "maze" |
| `cols, rows` | `int` | Dimensões do mapa |
| `n_paths` | `int` | Caminhos do Loop Central |
| `arc_noise` | `float` | Ondulação dos arcos |
| `branch_count` | `int` | Ramificações extras (Maze) |
| `branch_length` | `int` | Comprimento médio dos ramos |
| `main_path_bias` | `float` | Bias em direção ao END |
| `loop_regions` | `int` | Regiões de decisão |
| `reward_branches` | `int` | Becos com recompensa |
| `false_branches` | `int` | Ramos falsos |
| `false_branch_length` | `int` | Comprimento dos ramos falsos |
| `risk_shortcuts` | `int` | Atalhos de risco |
| `safe_detours` | `int` | Desvios seguros |
| `dead_end_ratio` | `float` | Fração de becos |
| `prob_*` (×10) | `float` | Probabilidade individual de cada poder |

**Configurações padrão das dificuldades:**

| Parâmetro | Fácil | Médio | Difícil |
|---|---|---|---|
| Tamanho | 24×14 | 36×20 | 56×30 |
| Generator | maze | maze | maze |
| challenge_profile | easy | medium | hard |
| branch_count | 7 | 10 | 18 |
| Poderes de perigo | Reduzidos | Balanceados | Amplificados |

**Progressão:** Menu → Fácil → Médio → Difícil → tela final. Cada transição:
1. Mostra tela de fim com vidas restantes e próxima dificuldade.
2. Recria contexto OpenGL, limpa cache de texturas, gera novo mapa, respawna cubo.

---
