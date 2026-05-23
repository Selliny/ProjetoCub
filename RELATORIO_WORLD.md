# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 6. Módulo `src/world/`

### 5.1 `Map` — `src/world/map.py` (977 linhas)

Gerencia o mundo do jogo: grid esparso de blocos, validação de movimento para o cubo, e geração procedural.

#### 5.1.1 Representação do Grid

Grid esparso: `dict[(col, row) → Block]`. Células vazias simplesmente não existem — sem alocação de memória para o vazio.

- **col** = eixo X (horizontal)
- **row** = eixo Z (profundidade)
- Altura Y dos blocos: sempre `0.0` (o `Block.HEIGHT = 0.1` é aplicado via `glScalef`)

#### 5.1.2 Constantes de Classe

| Constante | Tipo | Valor | Descrição |
|---|---|---|---|
| `DEFAULT_COLS` | `int` | `32` | Colunas padrão |
| `DEFAULT_ROWS` | `int` | `32` | Linhas padrão |
| `CELL_COLORS` | `dict` | `{1: marrom, 2: verde, 3: vermelho}` | Cores por tipo de célula |
| `PROB_HEAL` | `float` | `0.005` | Probabilidade base de HealBlock |
| `PROB_SHRINK` | `float` | `0.020` | Probabilidade base de ShrinkBlock |
| `PROB_GROW` | `float` | `0.015` | Probabilidade base de GrowBlock |
| `PROB_PORTAL` | `float` | `0.010` | Probabilidade base de PortalBlock |
| `PROB_ICE` | `float` | `0.030` | Probabilidade base de IceBlock |
| `PROB_INVERT` | `float` | `0.020` | Probabilidade base de InvertBlock |
| `PROB_FRAGILE` | `float` | `0.030` | Probabilidade base de FragileBlock |
| `PROB_BOUNCE` | `float` | `0.018` | Probabilidade base de BouncePadBlock |
| `PROB_SLOW` | `float` | `0.015` | Probabilidade base de SlowBlock |
| `PROB_CHECKPOINT` | `float` | `0.012` | Probabilidade base de CheckpointBlock |
| `FRAGILE_DELAY` | `float` | `1.5` | Segundos até desativar FragileBlock |
| `DEFAULT_N_PATHS` | `int` | `2` | Caminhos para Loop Central |
| `DEFAULT_ARC_NOISE` | `float` | `0.0` | Desvio orgânico dos arcos |

#### 5.1.3 Atributos de Instância

| Atributo | Tipo | Descrição |
|---|---|---|
| `_grid` | `dict[tuple[int,int], Block]` | Grid esparso principal |
| `start` | `tuple[int, int]` | Posição de início `(col, row)` |
| `direction` | `tuple[int, int]` | Direção inicial do cubo |
| `_fragile_timers` | `dict[tuple[int,int], float]` | `(col, row) → tempo_absoluto` |
| `_active_checkpoint` | `tuple[int,int] \| None` | Checkpoint atualmente ativo |

#### 5.1.4 API Pública — Manipulação do Grid

| Método | Assinatura | Descrição |
|---|---|---|
| `add_block` | `(block, col, row) → None` | Registra bloco na célula |
| `get_block` | `(col, row) → Block \| None` | Retorna bloco na célula |
| `remove_block` | `(col, row) → None` | Remove bloco da célula |
| `draw` | `() → None` | Desenha todos os blocos ativos |

#### 5.1.5 MovementValidator (protocolo duck-typed)

Interface implementada pelo `Map` e consumida pelo `Cube` via injeção em `try_roll()`.

| Método | Assinatura | Descrição |
|---|---|---|
| `can_move_to` | `(grid_x, grid_z) → bool` | True se bloco existe e está ativo |
| `get_tile_type` | `(grid_x, grid_z) → str` | `"empty"`, `"floor"` ou `"end"` |
| `get_power` | `(grid_x, grid_z) → str \| None` | Nome do poder do bloco ou None |
| `consume_power` | `(grid_x, grid_z) → None` | Substitui PoweredBlock por Block comum |
| `get_random_position` | `() → tuple[int, int]` | Posição aleatória (usada pelo portal) |
| `schedule_fragile` | `(grid_x, grid_z) → None` | Agenda desativação do FragileBlock |
| `set_checkpoint` | `(grid_x, grid_z) → None` | Ativa checkpoint; desativa o anterior |

#### 5.1.6 `Map.generate()` — Parâmetros

```python
Map.generate(
    cols=32, rows=32,           # Dimensões da grade
    seed=None,                   # Semente do RNG
    challenge_profile="medium",  # "easy" | "medium" | "hard"
    generator="loop",            # "loop" | "maze"
    n_paths=2,                   # Caminhos do Loop Central (2–4)
    arc_noise=0.0,               # Ondulação dos arcos [0.0, 1.0]
    branch_count=None,           # Ramificações extras (Maze)
    branch_length=None,          # Comprimento médio das ramificações
    main_path_bias=0.72,         # Bias em direção ao END (Maze)
    loop_regions=0,              # Regiões de loop alternativo
    reward_branches=0,           # Becos com recompensas
    false_branches=0,            # Bifurcações falsas
    false_branch_length=None,    # Comprimento médio dos falsos ramos
    risk_shortcuts=0,            # Atalhos perigosos
    safe_detours=0,              # Desvios seguros
    dead_end_ratio=0.35,         # Fração de ramos que viram becos
    prob_heal=0.005, ...         # Probabilidades individuais de cada poder
)
```

---

### 5.2 Processo de Geração Procedural

A geração ocorre em três estágios independentes:

```
Map.generate()
  ├─ [1] _build_matrix  (loop)  → matrix + start + direction
  │   ou _build_maze_matrix (maze) → matrix + start + direction + intents
  ├─ [2] _has_path / _path_analysis → valida conectividade + BFS de distâncias
  └─ [3] _matrix_to_map → converte inteiros em Block/PoweredBlock com poderes zonais
```

Valor das células na matriz intermediária: `0=vazio`, `1=chão`, `2=START`, `3=END`.

---

#### 5.2.1 Gerador Loop Central (`_build_matrix`)

**Resumo:** Geometria determinística. Dado `cols × rows`, produz sempre o mesmo esqueleto de anel; apenas `arc_noise` e `n_paths` variam a forma. Sem walker aleatório — conectividade garantida por construção.

##### Geometria fixa (Fase 1)

Toda a geometria é derivada apenas de `cols` e `rows`:

```
entrada_row = rows // 2 - 1          ← linha em que START aparece
entrada_len = max(2, cols // 6)      ← comprimento do corredor de entrada
saida_row   = entrada_row + 2        ← linha em que END aparece (2 abaixo)
saida_len   = max(2, cols // 7)      ← comprimento do corredor de saída

anel:
  topo = max(1, rows // 5)           ← linha mais alta do anel
  base = rows - max(2, rows // 4) - 1  ← linha mais baixa
  esq  = entrada_len + 1             ← coluna esquerda do anel
  dir  = cols - max(3, cols // 6) - 1  ← coluna direita do anel

bif (bifurcação) = (entrada_row, anel["esq"])
con (convergência) = (saida_row, anel["dir"])
```

Restrições de sanidade aplicadas automaticamente:
- `topo ≤ entrada_row - 1` e `topo ≥ 1`
- `base ≥ saida_row + 1` e `base ≤ rows - 2`
- `esq ≥ 1` e `dir ≤ cols - 2`

Layout resultante para um mapa 32×32:

```
col:  0   esq=5          dir=25  end_col
      │    │               │       │
row 0 ·    ·  ·  ·  ·  ·  ·  ·  ·  ·
    …
 topo=6    ┌───────────────────────┐
    …      │                       │
entrada=15 S ── ── ── bif          │ con ── ── E
 saida=16  ·          │            │ │
    …      │          │            │ │
 base=23   └───────────────────────┘
    …
```

##### Fases de escavação

| Fase | Condição | O que escava |
|---|---|---|
| 1 | sempre | Corredor START→bif e borda completa do anel (topo, base, esq, dir) + corredor con→END |
| 2 | sempre | Arco superior: bif sobe até topo, percorre borda top, desce até con |
| 3 | sempre | Arco inferior: bif desce até base, percorre borda bot, sobe até con |
| 4 | `n_paths ≥ 3` | Corredor interno horizontal: bif → linha_meio → con |
| 5 | `n_paths ≥ 4` | Atalho central: bif → centro do anel → con (em L) |

Linha do corredor interno (Fase 4):
```python
r_meio = (anel["topo"] + anel["base"]) // 2 + rng.randint(-1, 1)
# clampado em [topo+1, base-1]
```

##### Ruído nos arcos (`arc_noise`)

Aplicado individualmente a cada tile dos arcos superior e inferior (Fases 2 e 3). Para cada tile na borda do anel:

```python
if rng.random() < arc_noise:
    # desvia 1 célula para o interior:
    borda topo  → r+1  (desce)
    borda base  → r-1  (sobe)
    borda esq   → c+1  (entra)
    borda dir   → c-1  (entra)
    # só aplica se a célula destino for vazia (0)
```

Efeito: `arc_noise=0.0` → arcos perfeitamente retos; `arc_noise=0.5` → ~50% dos tiles desviam criando protuberâncias irregulares; `arc_noise=1.0` → arcos máximos irregulares (pode criar dead-ends visuais no anel, mas conectividade é garantida pelas fases anteriores).

##### Knobs do Loop Central — guia de game design

| Parâmetro | Range útil | Efeito no mapa |
|---|---|---|
| `cols × rows` | 24×14 → 56×30 | Escala total. Mapas maiores = mais espaço entre poderes, jornada mais longa |
| `n_paths` | 2, 3, 4 | 2=laço simples; 3=decisão no meio; 4=atalho central agressivo |
| `arc_noise` | 0.0 → 0.6 | 0=visual geométrico, 0.3=orgânico suave, >0.5=caótico mas válido |

> **Limite do gerador Loop:** Não produz dead-ends, becos ou rotas falsas. A estrutura é sempre um laço com 2–4 rotas entre START e END. Para mapas com exploração e tomada de decisão, use `generator="maze"`.

---

#### 5.2.2 Gerador Maze (`_build_maze_matrix`)

**Resumo:** Labirinto orgânico por **Drunkard Walk** dirigido. Produz mapas únicos a cada seed. A conectividade do caminho principal é garantida por fallback Manhattan; o resto é aleatório.

##### Posições fixas

```python
start = (1, rows // 2)              ← sempre na borda esquerda, meio vertical
end   = (cols - 2, rng.randint(1, rows - 2))  ← borda direita, altura aleatória
```

Borda de segurança: `inside(x, z)` exige `1 ≤ x ≤ cols-2` e `1 ≤ z ≤ rows-2`, impedindo que qualquer caminho toque as bordas externas da grade.

##### Etapa 1 — Caminho principal (Drunkard Walk)

```python
max_steps = (cols + rows) * 12    ← orçamento máximo de passos

# A cada passo:
# Com probabilidade main_path_bias → escolhe direção que reduz distância até END
# Senão → direção aleatória entre as 4 possíveis
```

A função `biased_direction(x, z)` calcula `preferred` como as direções que aproximam de `end` nos eixos X e/ou Z separadamente, depois sorteia entre elas se `rng.random() < main_path_bias`.

**Fallback Manhattan** (garante conectividade):
```python
while x != ex: x += 1 if ex > x else -1; carve(x, z)
while z != ez: z += 1 if ez > z else -1; carve(x, z)
```
Executado após o loop principal se o walker não chegou ao END dentro do orçamento.

Efeito de `main_path_bias`:
- `0.0` → walk completamente aleatório (mapa muito tortuoso, pode não chegar em `max_steps`, cai no fallback)
- `0.5` → orgânico, mistura boa de curvas e avanço
- `0.72` (padrão) → avança firmemente com desvios ocasionais
- `1.0` → caminho quase Manhattan, muito direto

##### Etapa 2 — Estruturas secundárias intencionais

Cada estrutura seleciona dois pontos `a` e `b` no caminho principal (dentro de uma janela que exclui os `margin = max(3, len(main_path)//8)` primeiros e últimos tiles), e escava um desvio entre eles via `carve_detour`.

**`carve_detour(a, b, intent)`:**
```python
span = abs(ax-bx) + abs(az-bz)
offset = max(2, min(rows//3, span//3))   # deslocamento lateral
if intent == "safe": offset += 2          # desvios safe são mais amplos
if rng.random() < 0.5: offset = -offset  # aleatoriza a direção do desvio

# Escava em L: a → waypoint → b
# Waypoint é deslocado lateralmente em X ou Z (50/50)
```

`mark_route(route, intent)` adiciona intents sobre a rota escavada:

| intent | Onde coloca | Powers usados |
|---|---|---|
| `"risk"` | A cada `len(route)//4` tiles (exceto extremos) | `fragile`, `ice`, `bounce`, `slow` |
| `"safe"` | No tile do meio (`route[len//2]`) | `checkpoint` (45%) ou `heal` (55%) |
| `"loop"` | No tile do meio (só se `len > 4`) | `slow`, `ice`, `heal` |

Gap mínimo entre pontos `a` e `b`:
```python
motif_gap = max(6, (cols + rows) // 8)
loop_regions  → gap = motif_gap
safe_detours  → gap = motif_gap + 2
risk_shortcuts → gap = max(4, motif_gap - 2)
```

##### Etapa 3 — Reward branches e false branches

**`carve_reward_branch()`:**
- Parte de um tile aleatório do caminho principal (janela central)
- Comprimento: `rng.randint(3, max(4, branch_length or 6))`
- Em cada passo: 25% chance de mudar direção
- Intent no último tile: `grow`, `checkpoint`, ou `slow` (1/3 cada)

**`carve_false_branch()`:**
- Parte de um tile aleatório do caminho principal
- Comprimento: `rng.randint(max_len//2, max_len)` onde `max_len = false_branch_length or max(5, branch_length or 8)`
- Evita ativamente recolocar o walker perto do caminho principal (`is_near_main_path`)
- Intent no último tile (se `len ≥ 3`): `slow`, `ice`, ou `grow` (1/3 cada)

##### Etapa 4 — Ramificações orgânicas

```python
if branch_count is None: branch_count = max(4, (cols * rows) // 70)
if branch_length is None: branch_length = max(4, (cols + rows) // 7)
```

Para cada ramificação:
- Parte de um tile floor/start aleatório já existente
- Passos: `rng.randint(branch_length//2, branch_length)`
- 55% chance de continuar na mesma direção do passo anterior
- `dead_end_ratio`: se `True`, o último tile recebe intent `slow` ou `ice`

##### Knobs do Maze — guia de game design

| Parâmetro | Range útil | Efeito no mapa |
|---|---|---|
| `main_path_bias` | 0.4 – 0.9 | 0.4=labiríntico/confuso, 0.72=balanceado, 0.9=quase reto |
| `branch_count` | 4 – 25 | Densidade de caminhos alternativos (padrão: `cols×rows÷70`) |
| `branch_length` | 4 – 15 | Comprimento médio de cada ramo (padrão: `(cols+rows)÷7`) |
| `dead_end_ratio` | 0.0 – 0.8 | Fração de ramos que terminam em bloco de perigo |
| `loop_regions` | 0 – 5 | Nº de loops alternativos intencionais (decisões estratégicas) |
| `reward_branches` | 0 – 6 | Nº de becos com recompensa explícita |
| `false_branches` | 0 – 8 | Nº de becos longos enganosos sem recompensa |
| `false_branch_length` | 5 – 20 | Comprimento dos becos falsos (mais longo = mais punitivo) |
| `risk_shortcuts` | 0 – 4 | Nº de atalhos perigosos (reduz distância, aumenta risco) |
| `safe_detours` | 0 – 4 | Nº de desvios longos mas seguros (checkpoint/heal no meio) |

**Combinações recomendadas para game design:**

| Perfil | `bias` | `branch_count` | `dead_end` | `loop` | `reward` | `false` | `risk` | `safe` |
|---|---|---|---|---|---|---|---|---|
| Tutorial | 0.85 | 4 | 0.1 | 0 | 3 | 0 | 0 | 2 |
| Exploração | 0.55 | 14 | 0.3 | 3 | 2 | 3 | 1 | 2 |
| Labirinto puro | 0.45 | 20 | 0.5 | 2 | 1 | 6 | 2 | 1 |
| Speedrun | 0.88 | 6 | 0.2 | 1 | 1 | 2 | 3 | 0 |
| Hard survival | 0.65 | 16 | 0.6 | 2 | 1 | 5 | 3 | 1 |

---

#### 5.2.3 Validação de Conectividade (`_has_path` + `_path_analysis`)

Executada por `generate()` antes de retornar o mapa. Se falhar → `RuntimeError`.

`_path_analysis` retorna dois artefatos que são reutilizados por `_matrix_to_map`:

```python
distance: dict[(col, row) → int]   # distância BFS do START
critical_path: set[(col, row)]      # tiles no caminho mais curto START→END
```

BFS padrão 4-direcional, `walkable = {1, 2, 3}`. O caminho crítico é reconstruído via rastreamento de `parent` de END até START.

---

#### 5.2.4 Distribuição de Poderes (`_matrix_to_map`)

Aplicada sobre qualquer matriz — tanto Loop quanto Maze compartilham esse estágio.

##### Pipeline por célula de chão

```
célula valor == 1 (chão):
  ┌── tem intent (Maze only)?
  │     └── intent_allowed(intent, zone, is_critical)?
  │           → _make_powered(intent, pos)          ✓ usa intent
  │           → fallback para choose_special()       ✗ intent proibido
  └── sem intent:
        └── choose_special(col, row)
              → _make_powered(power, pos)            se power != None
              → Block normal                          se power == None
```

##### Zoneamento (`zone_for`)

```python
zone = distance_from_start[(col, row)] / max_distance   # ∈ [0.0, 1.0]
```

`max_distance` é o maior valor no dicionário `distance` — normalmente a distância até o END.

##### Regras de `intent_allowed`

| Condição | Powers bloqueados |
|---|---|
| `zone < 0.18` | Todos os dangers: shrink, portal, ice, invert, fragile, bounce, slow |
| `zone < 0.28` | portal, fragile, bounce, invert |
| `zone > 0.88` | portal, checkpoint |
| `is_critical == True` | portal, fragile, bounce |

A zona de entrada (18% inicial) é sempre segura. A zona final (últimos 12%) não tem portais nem checkpoints. O caminho mais curto nunca tem portal/fragile/bounce — evita que o jogador seja penalizado na rota óbvia.

##### Sorteio ponderado (`choose_special`)

```python
# Para cada power:
weight = base_prob × zone_weight(name, base, zone, is_critical)

total = sum(weights)
if total <= 0 or rng.random() >= min(total, 0.42):
    return None   # bloco normal

# Sorteio ponderado proporcional:
pick = rng.random() * total
acc = 0
for name, weight in weighted:
    acc += weight
    if pick <= acc: return name
```

O `min(total, 0.42)` garante o **cap global de 42%** — mesmo que as probabilidades somadas passem desse valor, o dado continua sendo tirado contra `0.42`. Isso significa: em nenhum cenário mais de 42% das células terão qualquer poder especial.

##### Multiplicadores por zona e perfil (valores exatos do código)

**Zona 0–20% (início)**

| Power | Easy | Medium | Hard |
|---|---|---|---|
| heal | 0.65× | 0.25× | 0.08× |
| grow | 0.45× | 0.20× | 0.08× |
| checkpoint | 0.70× | 0.45× | 0.20× |
| (qualquer danger) | 0.0× | 0.0× | 0.0× |

**Zona 20–45% (início-meio)**

| Power | Easy | Medium | Hard |
|---|---|---|---|
| heal | 1.15× | 0.85× | 0.35× |
| grow | 1.0× | 0.80× | 0.55× |
| checkpoint | 1.25× | 1.0× | 0.75× |
| ice | 0.45× | 0.70× | 0.85× |
| slow | 0.35× | 0.65× | 0.85× |
| shrink | 0.25× | 0.60× | 0.80× |
| invert | 0.20× | 0.45× | 0.70× |
| fragile | 0.20× | 0.45× | 0.75× |
| bounce | 0.25× | 0.50× | 0.75× |
| portal | 0.10× | 0.25× | 0.35× |

**Zona 45–75% (meio)**

| Power | Easy | Medium | Hard |
|---|---|---|---|
| heal | 1.0× | 0.65× | 0.25× |
| grow | 1.0× | 0.85× | 0.65× |
| checkpoint | 1.0× | 0.90× | 0.55× |
| ice | 0.70× | 1.0× | 1.25× |
| slow | 0.65× | 0.95× | 1.20× |
| shrink | 0.50× | 0.95× | 1.15× |
| invert | 0.45× | 0.85× | 1.15× |
| fragile | 0.45× | 0.85× | 1.25× |
| bounce | 0.55× | 0.85× | 1.10× |
| portal | 0.25× | 0.55× | 0.65× |

**Zona 75–100% (final)**

| Power | Easy | Medium | Hard |
|---|---|---|---|
| heal | 0.75× | 0.45× | 0.12× |
| grow | 0.80× | 0.70× | 0.50× |
| checkpoint | 0.35× | 0.25× | **0.0×** |
| ice | 0.80× | 1.15× | 1.45× |
| slow | 0.70× | 1.05× | 1.35× |
| shrink | 0.60× | 1.0× | 1.30× |
| invert | 0.50× | 1.0× | 1.30× |
| fragile | 0.55× | 1.0× | **1.55×** |
| bounce | 0.55× | 0.95× | 1.25× |
| portal | 0.15× | 0.30× | 0.35× |

> **Leitura:** checkpoint em Hard zona final = `0.012 × 0.0 = 0`. Fragile em Hard zona final = `0.030 × 1.55 = 0.0465` antes do cap.

##### Probabilidades base e peso efetivo máximo possível

| Power | `base_prob` | Máx. multiplier (Hard, zona 75–100%) | Peso máx. antes do cap |
|---|---|---|---|
| heal | 0.005 | 0.75× (Easy) | 0.00375 |
| shrink | 0.020 | 1.30× (Hard) | 0.0260 |
| grow | 0.015 | 1.0× (Easy) | 0.0150 |
| portal | 0.010 | 0.65× (Hard) | 0.0065 |
| ice | 0.030 | **1.45×** (Hard) | **0.0435** |
| invert | 0.020 | 1.30× (Hard) | 0.0260 |
| fragile | 0.030 | **1.55×** (Hard) | **0.0465** |
| bounce | 0.018 | 1.25× (Hard) | 0.0225 |
| slow | 0.015 | 1.35× (Hard) | 0.0203 |
| checkpoint | 0.012 | 1.25× (Easy início-meio) | 0.0150 |

> Ice e Fragile têm os maiores pesos possíveis em Hard zona final — são os poderes mais prováveis nos estágios avançados do jogo difícil.

##### Knobs de probabilidade — guia de game design

| Objetivo | Ajuste sugerido |
|---|---|
| Mapa quase sem poderes | Todas as `prob_*` em 0.002–0.005 |
| Mapa tutorial com apoio | `prob_heal=0.04`, `prob_checkpoint=0.05`, `prob_grow=0.03`, dangers em 0 |
| Mapa de risco extremo | `prob_fragile=0.08`, `prob_ice=0.06`, `prob_invert=0.04`, rewards em 0 |
| Mapa balanceado | Valores padrão + `challenge_profile="medium"` |
| Checkpoint frequente | `prob_checkpoint=0.04` (padrão 0.012) |
| Reduzir caos de portal | `prob_portal=0.0` (desabilita completamente) |

---

### 5.3 `Scene` — `src/world/scene.py` (20 linhas)

Agregador mínimo de `Cube` e `Map`.

**Atributos:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `cube` | `Cube` | Cubo jogável |
| `map` | `Map` | Mapa atual |

**Métodos:**

| Método | Descrição |
|---|---|
| `draw()` | `glDisable(GL_CULL_FACE)`, chama `cube.draw()` e `map.draw()` |

> **Nota:** `Scene` está disponível mas não é utilizado pelo `main.py`, que gerencia `Cube` e `Map` diretamente para maior controle sobre o render e câmera.

---
