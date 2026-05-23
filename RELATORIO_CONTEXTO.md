# Mapa de Contexto — Relatórios ProjetoCub

**Gerado em:** 2026-05-22 | Branch `main` | Commit `473903c`

Este arquivo indexa os relatórios modulares do projeto. Cada entrada descreve o escopo e os tópicos cobertos pelo arquivo correspondente.

---

## [RELATORIO_VISAO_GERAL_E_ESTRUTURA.md](RELATORIO_VISAO_GERAL_E_ESTRUTURA.md)
**Escopo:** Apresentação geral da aplicação e organização de arquivos.

- Propósito do projeto (jogo 3D educacional, conceitos de CG)
- Stack tecnológico: Python 3.11+, pygame 2.6.1, PyOpenGL 3.1.7, numpy 2.1.3
- Árvore completa de diretórios com papel de cada arquivo (`src/`, `sandboxes/`, `assets/`)

---

## [RELATORIO_GRAPHICS.md](RELATORIO_GRAPHICS.md)
**Escopo:** Primitivas de computação gráfica reutilizáveis em `src/graphics/`.

| Classe | Papel |
|---|---|
| `Color` | Encapsulamento RGBA; emite `glColor4f` |
| `Position` | Vetor 3D; emite `glTranslatef` |
| `Size` | Fatores de escala por eixo; emite `glScalef`; método `uniform()` |
| `Camera` | Câmera esférica yaw/pitch/zoom/tilt; disponível mas não usada pelo `main.py` |
| `TextureManager` | Cache estático de IDs OpenGL; carregamento lazy via `pygame.image.load` |

---

## [RELATORIO_ENTITIES_CUBE.md](RELATORIO_ENTITIES_CUBE.md)
**Escopo:** Entidade jogável `Cube` em `src/entities/cube.py` (704 linhas).

- Enum `CubeState`: IDLE, ROLLING, SLIDING, FALLING, FADING_OUT, FADING_IN
- Constantes de temporização (ROLL_DURATION, FALL_DURATION, FADE_DURATION, ICE_STEPS…)
- Atributos de instância agrupados: posição/grid, estado de jogo, animação de roll, queda/fade, deslizamento de gelo, poderes temporários, portal
- Propriedades públicas: `controls_inverted`, `reached_end`, `checkpoint_active`, `is_dead`
- Métodos públicos e privados com assinaturas
- Diagrama ASCII da state machine completa
- Tabela de reação a cada um dos 10 poderes em `_finish_roll()`

---

## [RELATORIO_ENTITIES_BLOCK.md](RELATORIO_ENTITIES_BLOCK.md)
**Escopo:** Hierarquia de blocos do mapa em `src/entities/block.py` (589 linhas).

- Classe base `Block`: constantes (HEIGHT=0.1), atributos de instância, métodos de renderização
- Multiplicadores de brilho por face (topo, frente/trás, lados, base)
- Árvore de herança: `StartBlock`, `EndBlock`, `PoweredBlock` → 10 subclasses
- Tabela de cada subclasse: cor RGB, textura, nome do poder, visual extra (triângulos, linhas GL, overlays blend)
- Atributos extras de `CheckpointBlock` (`is_active_checkpoint`) e `FragileBlock` (`_deactivate_at`, `_blink_t`)

---

## [RELATORIO_WORLD.md](RELATORIO_WORLD.md)
**Escopo:** Geração procedural e gestão do mundo em `src/world/` (map.py + scene.py).

- Representação esparsa: `dict[(col, row) → Block]`
- Constantes e probabilidades base de cada tipo de bloco
- Protocolo `MovementValidator` (duck-typed): 7 métodos consumidos pelo `Cube`
- Assinatura completa de `Map.generate()` com todos os parâmetros
- **Gerador Loop Central** (`_build_matrix`): fórmulas exatas de geometria (entrada_row, anel, bif, con), 5 fases de escavação, comportamento de `arc_noise` por tile, tabela de knobs com ranges úteis
- **Gerador Maze** (`_build_maze_matrix`): Drunkard Walk dirigido com `main_path_bias`, fallback Manhattan, `carve_detour` com offset lateral, `mark_route` por intent; tabela de knobs + 5 combinações recomendadas (tutorial/exploração/labirinto/speedrun/hard)
- **Validação BFS** (`_path_analysis`): produz `distance` e `critical_path` reutilizados na distribuição
- **Distribuição de poderes** (`_matrix_to_map`): pipeline por célula (intent → choose_special → Block), regras exatas de `intent_allowed`, fórmula do cap 42%, tabelas completas de multiplicadores por zona (4 faixas) × perfil × power, pesos máximos calculados, knobs de probabilidade por objetivo de game design
- `Scene`: agregador mínimo Cube + Map; razão por não ser usado no `main.py`

---

## [RELATORIO_INPUT_E_MAIN.md](RELATORIO_INPUT_E_MAIN.md)
**Escopo:** Camada de input e orquestração principal em `src/input/` e `main.py`.

- `InputHandler`: mapeamento tecla → `(dx, dz)` → `try_roll()`; supersedido por polling direto
- `main.py` — sequência de inicialização (menu → pygame/OpenGL → mapa → cubo → câmera)
- Game loop 60 FPS: eventos, update (map + cube), leitura de input com inversão de controles
- Câmera orbital com lerp (factor 8.0×dt), `camera_distance=12`, `camera_height=8`
- HUD 2D via projeção ortogonal + `glDrawPixels`: corações e legenda de 10 poderes
- `DifficultyConfig` (31 campos): tabela de parâmetros e configurações por dificuldade (Fácil/Médio/Difícil)
- Fluxo de progressão: Menu → Fácil → Médio → Difícil → tela final; recriação de contexto OpenGL entre níveis

---

## [RELATORIO_SANDBOXES_E_PIPELINE.md](RELATORIO_SANDBOXES_E_PIPELINE.md)
**Escopo:** Ambientes de teste isolados e pipeline de renderização OpenGL.

- `_harness.py`: framework compartilhado (janela, câmera, loop 60 FPS, callbacks)
- `sandbox_cube.py`: integração completa Cubo + Mapa + Câmera + HUD
- `sandbox_block.py`: inspeção visual de bloco único; toggle tipo/cor/active
- `sandbox_map.py`: editor de grid; cursor WASD + regeneração procedural
- `sandbox_scene.py`: smoke test do agregador `Scene`
- `menu.py`: estética retro CRT, cubo girando, `DifficultyConfig`, tela de fim
- **Pipeline OpenGL** (Immediate Mode): configuração única (viewport, perspective, depth test), loop por frame (clear → lookAt → blocos → cubo → HUD ortogonal → flip)
- Tabela de 14 técnicas OpenGL utilizadas (glPushMatrix, glBlend, glDepthFunc, glDrawPixels, GL_QUADS, GL_LINES, GL_TRIANGLES, GL_LINE_LOOP…)

---

## [RELATORIO_MECANICAS_PADROES_ESTADO.md](RELATORIO_MECANICAS_PADROES_ESTADO.md)
**Escopo:** Mecânicas de jogo, padrões de design e estado atual da aplicação.

- Movimento: roll 0.25s (slow: 0.5s), fila de 1 comando, inversão de controles
- Tabela dos 10 poderes: duração, se é consumido, efeito no cubo
- Sistema de vidas (3 iniciais) e respawn (checkpoint ativo ou último tile walkable)
- Condição de vitória: `reached_end && state == IDLE`
- **8 padrões de design** identificados: Composição, State Machine, Protocol/Duck Typing, Lazy Caching, Command Queue, Observer parcial, Template Method, Factory Method
- Funcionalidades implementadas vs. limitações (áudio, VFX, save/load, OpenGL moderno, testes unitários)
- Tabela de arquivos com contagem de linhas (~4.582 total)
