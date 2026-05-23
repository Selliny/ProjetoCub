# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 4. Módulo `src/entities/`

### 4.1 `Cube` — `src/entities/cube.py` (704 linhas)

Entidade principal controlada pelo jogador. Implementa uma **state machine** completa para animações, física de queda e efeitos de poderes.

#### 4.1.1 Enumeração `CubeState`

| Estado | String | Descrição |
|---|---|---|
| `IDLE` | `"idle"` | Aguardando input; pode iniciar rolls |
| `ROLLING` | `"rolling"` | Animação de tombamento em andamento |
| `SLIDING` | `"sliding"` | Deslizamento plano (IceBlock, sem rotação) |
| `FALLING` | `"falling"` | Queda vertical após sair do mapa |
| `FADING_OUT` | `"fading_out"` | Fade de saída (portal/respawn) |
| `FADING_IN` | `"fading_in"` | Fade de entrada (portal/respawn) |

#### 4.1.2 Constantes de Classe

| Constante | Tipo | Valor | Descrição |
|---|---|---|---|
| `ROLL_DURATION` | `float` | `0.25` | Duração do roll normal (s) |
| `FALL_DURATION` | `float` | `0.5` | Duração da queda (s) |
| `FALL_DISTANCE` | `float` | `3.0` | Distância vertical da queda (unidades) |
| `FADE_DURATION` | `float` | `0.4` | Duração de cada fase do fade (s) |
| `TILE_SIZE` | `float` | `1.0` | Lado de cada célula do grid (unidades) |
| `MAX_LIVES` | `int` | `3` | Vidas iniciais padrão |
| `INVERT_DURATION` | `float` | `5.0` | Duração dos controles invertidos (s) |
| `SLOW_MOVES` | `int` | `3` | Movimentos lentos após SlowBlock |
| `SLOW_FACTOR` | `float` | `2.0` | Multiplicador da duração do roll lento |
| `ICE_STEPS` | `int` | `3` | Passos do deslize de gelo |
| `SLIDE_STEP_DURATION` | `float` | `0.12` | Duração de cada passo do slide (s) |

#### 4.1.3 Atributos de Instância

**Posição e Grid:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `grid_x` | `float` | Coluna atual no grid (inteiro ou .25/.75 quando encolhido) |
| `grid_z` | `float` | Linha atual no grid |
| `position` | `Position` | Posição 3D sincronizada com grid |
| `step_size` | `float` | Distância por roll: `1.0` (normal) ou `0.5` (shrink) |
| `_spawn_grid_x` | `int` | Coluna do spawn original |
| `_spawn_grid_z` | `int` | Linha do spawn original |
| `_spawn_y` | `float` | Altura Y do spawn |
| `_last_valid_grid_x` | `int` | Último tile walkable visitado |
| `_last_valid_grid_z` | `int` | Último tile walkable visitado |

**Estado de Jogo:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `lives` | `int` | Vidas restantes |
| `max_lives` | `int` | Máximo de vidas |
| `state` | `CubeState` | Estado atual da state machine |
| `color` | `Color` | Cor do cubo |
| `size` | `Size` | Escala atual do cubo |
| `_reached_end` | `bool` | True ao pisar no EndBlock |

**Animação de Roll:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_roll_t` | `float` | Progresso do roll [0.0, 1.0] |
| `_pending_dx` | `int` | Direção X do roll em andamento |
| `_pending_dz` | `int` | Direção Z do roll em andamento |
| `_queued` | `tuple \| None` | Comando enfileirado `(dx, dz, validator)` |
| `_validator` | `MovementValidator \| None` | Validador do roll em andamento |
| `_total_angle_z` | `float` | Rotação acumulada em torno do eixo Z (roll lateral) |
| `_total_angle_x` | `float` | Rotação acumulada em torno do eixo X (roll frontal) |

**Animação de Queda e Fade:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_fall_t` | `float` | Progresso da queda [0.0, 1.0] |
| `_fall_offset_y` | `float` | Deslocamento Y atual durante a queda |
| `_fade_t` | `float` | Progresso do fade [0.0, 1.0] |
| `_alpha` | `float` | Opacidade atual [0.0, 1.0] |

**Deslizamento de Gelo:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_ice_slide_dx` | `int` | Direção X do slide a iniciar |
| `_ice_slide_dz` | `int` | Direção Z do slide a iniciar |
| `_slide_dx` | `int` | Direção X do slide em andamento |
| `_slide_dz` | `int` | Direção Z do slide em andamento |
| `_slide_steps` | `int` | Passos restantes do slide |
| `_slide_t` | `float` | Progresso do passo atual [0.0, 1.0] |
| `_slide_from_x` | `float` | Posição X no início do passo |
| `_slide_from_z` | `float` | Posição Z no início do passo |
| `_slide_validator` | `MovementValidator \| None` | Validador do slide |

**Poderes Temporários:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_invert_timer` | `float` | Tempo restante de inversão (s) |
| `_slow_moves_left` | `int` | Movimentos restantes com roll lento |
| `_checkpoint_x` | `int \| None` | Coluna do checkpoint ativo |
| `_checkpoint_z` | `int \| None` | Linha do checkpoint ativo |

**Portal:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `_portal_target_x` | `int` | Coluna de destino do portal |
| `_portal_target_z` | `int` | Linha de destino do portal |
| `_portal_landing_is_void` | `bool` | Se o destino do portal é vazio |

#### 4.1.4 Propriedades

| Propriedade | Tipo | Descrição |
|---|---|---|
| `controls_inverted` | `bool` | `True` se `_invert_timer > 0` |
| `reached_end` | `bool` | `True` se pisou no EndBlock |
| `checkpoint_active` | `bool` | `True` se `_checkpoint_x is not None` |
| `is_dead` | `bool` | `True` se `lives <= 0` |

#### 4.1.5 Métodos Públicos

| Método | Assinatura | Descrição |
|---|---|---|
| `try_roll` | `(dx, dz, validator) → bool` | Inicia roll ou enfileira; retorna True se aceito |
| `start_roll` | `(direction, axis="z") → None` | API legada; converte eixo em dx/dz |
| `update` | `(dt) → None` | Avança todas as animações e timers |
| `apply_transform` | `() → None` | Aplica transforms OpenGL (translate/rotate/scale) |
| `draw` | `() → None` | Renderiza o cubo com blending se alpha < 1 |
| `is_moving` | `() → bool` | True se ROLLING ou SLIDING |
| `is_rolling` | `() → bool` | True se ROLLING |
| `get_grid_position` | `() → tuple[int, int]` | Retorna `(grid_x, grid_z)` |
| `get_next_position` | `(dx, dz) → tuple[int, int]` | Próxima posição se mover em dx/dz |
| `on_tile_enter` | `(tile_type) → None` | Reage ao tipo do tile: "end"→vitória, !floor→queda |
| `respawn` | `() → None` | Retorna ao spawn original e reseta estado |
| `move` | `(dx, dy, dz) → None` | Move posição diretamente (API legada) |
| `scale` | `(factor) → None` | Escala uniforme direta (API legada) |

#### 4.1.6 Métodos Privados

| Método | Descrição |
|---|---|
| `_normalize_direction(dx, dz)` | Clampa para {-1, 0, 1}; rejeita diagonais |
| `_is_walkable(tile)` | Tile é "floor" ou "end" |
| `_enqueue_roll(dx, dz, validator)` | Guarda até 1 comando pendente |
| `_start_roll(dx, dz, validator)` | Seta estado e inicia animação |
| `_finish_roll()` | Snap no grid, acumula rotação, reage ao poder |
| `_start_ice_slide(dx, dz, validator)` | Inicia 3 passos de deslize de gelo |
| `_finish_slide_step()` | Conclui passo, verifica tile, continua ou para |
| `_apply_slide_transform()` | Interpolação linear horizontal (sem rotação) |
| `_start_fall()` | -1 vida, inicia estado FALLING |
| `_start_portal(target_x, target_z)` | Inicia sequência FADING_OUT |
| `_sync_position_from_grid()` | Atualiza `position` a partir de `grid_x/grid_z` |
| `_apply_roll_transform()` | Interpola rotação em torno do pivô da borda |
| `_apply_accumulated_rotation()` | Aplica `glRotatef` com ângulos acumulados |
| `_apply_size()` | Chama `glScalef` com tamanho atual |

#### 4.1.7 Fluxo da State Machine

```
               ┌───────┐
               │  IDLE │◄──────────────────────────────────────┐
               └───┬───┘                                        │
        try_roll() │                                           IDLE
               ┌───▼─────┐     _finish_roll()      ┌───────────┴─────┐
               │ ROLLING  │───────────────────────► │  Verifica tile  │
               └─────────┘                          └────┬───────┬────┘
                                                  walkable│    void│
                                                    ┌─────▼──┐  ┌──▼──────┐
                                                    │ice power│  │ FALLING │
                                                    └────┬────┘  └──┬──────┘
                                               SLIDING  │    após 0.5s │
                                              ┌──────────▼──┐        │
                                              │   SLIDING   │        │
                                              └──────┬──────┘        │
                                               steps=0│               │
                                                      └────► IDLE     │
                                                                       │
                                                              ┌────────▼────┐
                                                              │ FADING_IN   │
                                                              └────┬────────┘
                                                           alpha=1 │
                                                      landing void? │
                                                    Sim ► FALLING   │
                                                    Não ►──────────► IDLE
```

#### 4.1.8 Sistema de Poderes (em `_finish_roll`)

Ao finalizar um roll, o cubo consulta o validador para obter `tile_type` e `power` da célula de destino. A lógica de cada poder:

| Poder | Gatilho | Ação no Cubo | Consumido? |
|---|---|---|---|
| `shrink` | step_size == 1.0 | `step_size=0.5`, `size=0.5`, offset -0.25 | Não |
| `grow` | step_size == 0.5 | `step_size=1.0`, `size=1.0`, snap para grid | Sim |
| `heal` | lives < max_lives | `lives += 1` | Sim |
| `portal` | sempre | `_start_portal(tx, tz)` com posição aleatória | Sim |
| `ice` | sempre | Salva direção em `_ice_slide_dx/dz` | Não |
| `invert` | sempre | Toggle `_invert_timer` (5s ou 0) | Sim |
| `fragile` | sempre | Chama `validator.schedule_fragile(x, z)` | Não |
| `bounce` | dx!=0 ou dz!=0 | Teletransporta 2 casas (ou 1 se 2ª vazia) | Não |
| `slow` | sempre | `_slow_moves_left = 3` | Sim |
| `checkpoint` | sempre | `_checkpoint_x/z = (x, z)` | Não |

---
