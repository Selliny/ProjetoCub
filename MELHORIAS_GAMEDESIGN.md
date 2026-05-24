# Melhorias de Game Design — ProjetoCub

**Versão:** 0.1 (2026-05-23)  
**Base:** `GAMEDESIGN.md` v0.2, branch `main`, commit `6425910`

> Este documento detalha as alterações necessárias para melhorar a jogabilidade do ProjetoCub. Cada seção descreve o problema, o que deve mudar, os arquivos envolvidos, o algoritmo de implementação e as dependências. Não define o estado final implementado — serve como especificação técnica para cada melhoria.

---

## Índice

1. [Rebalancear geração de mapas (DifficultyConfig)](#1-rebalancear-geração-de-mapas-difficultyconfig)
2. [Obstáculos físicos móveis (WallBlock dinâmico)](#2-obstáculos-físicos-móveis-wallblock-dinâmico)
3. [Controle de densidade e combinações de poderes](#3-controle-de-densidade-e-combinações-de-poderes)
4. [Ocultar EndBlock e limitar campo visual](#4-ocultar-endblock-e-limitar-campo-visual)
5. [Ajustes nos poderes dos blocos existentes](#5-ajustes-nos-poderes-dos-blocos-existentes)

---

## 1. Rebalancear geração de mapas (DifficultyConfig)

### Problema

Os parâmetros atuais de `DifficultyConfig` em `sandboxes/menu.py` produzem mapas com deficiências estruturais identificadas em `GAMEDESIGN.md` (seção 2.2, problemas G1–G7):

- **G1** — Fácil (24×14 = 336 tiles, `main_path_bias=0.78`) é tão pequeno e linear que o jogador vai quase em linha reta do START ao END. Não há espaço para ramos, exploração ou dilema de rota.
- **G2** — Difícil (56×30 = 1680 tiles) extrapola o campo visual da câmera, criando desorientação passiva em vez de desafio de habilidade.
- **G4** — `loop_regions` cai de 2 para 1 no Difícil, reduzindo as únicas estruturas que criam decisão estratégica genuína — o inverso do esperado.
- **G5** — Razão `shrink:grow = 15:1` no Difícil (`prob_shrink=0.030`, `prob_grow=0.002`): o cubo encolhe permanentemente sem possibilidade prática de recuperação.
- **G6** — `risk_shortcuts=1` em todas as dificuldades; atalhos de risco não escalam com a dificuldade.
- **G7** — Densidade de cura colapsa no Difícil: 5× mais tiles, mas ~13× menos HealBlocks esperados.

### O que muda

Apenas valores numéricos em `sandboxes/menu.py`, dentro do dicionário `_DIFFICULTIES`. Nenhum código novo é necessário.

**Tabela completa — atual vs. proposto:**

| Parâmetro | Fácil atual | Fácil proposto | Médio atual | Médio proposto | Difícil atual | Difícil proposto |
|---|---|---|---|---|---|---|
| `cols × rows` | 24×14 | **32×18** | 36×20 | 36×22 | 56×30 | **44×26** |
| `main_path_bias` | 0.78 | **0.72** | 0.62 | 0.62 | 0.52 | **0.55** |
| `branch_count` | 7 | **10** | 10 | **12** | 18 | 18 |
| `branch_length` | 7 | **8** | 11 | 11 | 18 | **16** |
| `dead_end_ratio` | 0.20 | **0.25** | 0.48 | **0.45** | 0.68 | **0.65** |
| `loop_regions` | 2 | **3** | 2 | **3** | 1 | **4** |
| `reward_branches` | 3 | **4** | 2 | 2 | 1 | 1 |
| `false_branches` | 2 | 2 | 5 | 5 | 10 | 10 |
| `false_branch_length` | 5 | 5 | 11 | 11 | 18 | **14** |
| `risk_shortcuts` | 1 | 1 | 1 | **2** | 1 | **3** |
| `safe_detours` | 2 | **3** | 0 | **1** | 0 | 0 |
| `prob_heal` | 0.040 | **0.035** | 0.005 | 0.005 | 0.001 | **0.004** |
| `prob_shrink` | 0.006 | 0.006 | 0.025 | **0.020** | 0.030 | **0.018** |
| `prob_grow` | 0.006 | 0.006 | 0.002 | **0.006** | 0.002 | **0.010** |
| `prob_checkpoint` | 0.020 | 0.020 | 0.012 | 0.012 | 0.008 | **0.012** |
| (demais poderes) | sem mudança | — | sem mudança | — | sem mudança | — |

> Valores em **negrito** diferem do atual.

**Racional por mudança:**

- `cols/rows` Fácil: +71% de área cria espaço para ramos existirem.
- `cols/rows` Difícil: redução de 1680→1144 mantém o mapa grande mas dentro do campo visual útil da câmera (distance=12, height=9).
- `loop_regions` Difícil: 1→4 inverte a regressão atual; o Difícil passa a ter mais decisões estratégicas, não menos.
- `risk_shortcuts` Médio/Difícil: 1→2/3 cria escala real de atalhos de risco entre dificuldades.
- `prob_shrink/prob_grow` Difícil: ratio 15:1 → 1.8:1; Shrink passa a ser desafio gerenciável.
- `prob_heal` Difícil: 0.001→0.004 ainda é escasso mas não invisível em 1144 tiles.
- `prob_checkpoint` Difícil: 0.008→0.012 compensa a jornada mais longa.

### Arquivos envolvidos

| Arquivo | Papel |
|---|---|
| `sandboxes/menu.py` | Único arquivo alterado. Linha ~74-159: dicionário `_DIFFICULTIES` com os 3 objetos `DifficultyConfig`. |

### Detalhe de implementação

Localizar cada bloco de `DifficultyConfig(...)` no `_DIFFICULTIES` e substituir os valores marcados na tabela acima. Não há lógica condicional — são literais numéricos.

```python
# Exemplo — trecho Difícil (antes):
DifficultyConfig(
    label="Difícil", cols=56, rows=30,
    main_path_bias=0.52, loop_regions=1,
    risk_shortcuts=1, prob_shrink=0.030, prob_grow=0.002,
    prob_heal=0.001, prob_checkpoint=0.008,
    ...
)

# Depois:
DifficultyConfig(
    label="Difícil", cols=44, rows=26,
    main_path_bias=0.55, loop_regions=4,
    risk_shortcuts=3, prob_shrink=0.018, prob_grow=0.010,
    prob_heal=0.004, prob_checkpoint=0.012,
    ...
)
```

### Dependências

Nenhuma. Esta melhoria é independente e pode ser aplicada isoladamente.

---

## 2. Obstáculos físicos móveis (WallBlock dinâmico)

### Problema

Atualmente não existem obstáculos físicos no grid — tiles são ou chão walkable ou void (ausência). Nada bloqueia o movimento além das bordas do mapa. O jogador pode estudar o layout completo e executar qualquer rota sem impedimentos físicos. A ausência de obstáculos elimina toda mecânica de timing, esquiva e leitura de padrão.

Referência: `GAMEDESIGN.md` seção 3 (Vetor C — Obstáculos no grid) e seção 4.3 (C1 — WallBlock, C3 — MovingBlock).

### O que muda

Introduzir uma nova subclasse `MovingWallBlock` (ou `PatrolBlock`) que:

1. Ocupa uma posição no `_grid` do Map.
2. Tem um trajeto fixo de patrulha (dois pontos extremos em eixo horizontal ou vertical).
3. Move-se entre os dois extremos em ciclos de tempo (`patrol_speed` segundos por tile).
4. Ao mover, atualiza sua posição no `_grid`: remove da posição atual, insere na próxima.
5. É impassável: `can_move_to` retorna `False` para a posição ocupada pelo bloco.
6. Se o bloco mover para a posição atual do Cube: Cube perde 1 vida e executa respawn (mesma consequência de cair no void).

### Arquivos envolvidos

| Arquivo | Papel |
|---|---|
| `src/entities/block.py` | Adicionar `MovingWallBlock` como nova subclasse de `Block`. Adicionar `update(dt)` nesta subclasse. |
| `src/world/map.py` | Adicionar lista `_moving_blocks: list[MovingWallBlock]` ao Map. Chamar `block.update(dt)` para cada elemento em `Map.update(dt)`. Garantir que `_grid` seja atualizado atomicamente a cada movimento. |
| `sandboxes/menu.py` | Adicionar campo `prob_wall` ao `DifficultyConfig` (probabilidade base de tile virar MovingWallBlock). |
| `main.py` | Nenhuma mudança necessária — `map_.update(dt)` já é chamado; `map_.draw()` já itera o grid. |

### Detalhe de algoritmo

#### 2.1 Estrutura de MovingWallBlock

```python
class MovingWallBlock(Block):
    PATROL_COLOR = Color(0.3, 0.3, 0.35, 1.0)  # cinza metálico
    HEIGHT_VISUAL = 0.6  # mais alto que tile normal (0.1) para ser obstáculo visível

    def __init__(self, position, axis, point_a, point_b, speed=1.0):
        super().__init__(position, color=PATROL_COLOR)
        self.axis = axis          # 'x' (col) ou 'z' (row)
        self.point_a = point_a    # (col, row) — extremo A
        self.point_b = point_b    # (col, row) — extremo B
        self.speed = speed        # tiles por segundo
        self._target = point_b    # destino atual
        self._t = 0.0             # interpolação [0, 1] entre posição atual e target
        self._grid_pos = point_a  # posição atual no grid (inteiros)
```

#### 2.2 Lógica de update(dt)

```
update(dt):
    _t += speed * dt
    if _t >= 1.0:
        _t -= 1.0
        _grid_pos = _target
        _target = point_a if _target == point_b else point_b
        # Notificar o Map para atualizar _grid
        _on_move_callback(_grid_pos)  # injeta callback via __init__
    # Posição visual interpolada (suave):
    pos_visual = lerp(_grid_pos, _target, _t)
    self.position = Position(pos_visual.col, 0.0, pos_visual.row)
```

O callback `_on_move_callback` é injetado pelo Map ao criar o bloco. Ele executa:

```
on_move(new_grid_pos):
    del _grid[old_pos]
    _grid[new_grid_pos] = self
    # Verificar colisão com o Cube:
    if new_grid_pos == cube.get_grid_position():
        cube.hit_by_wall()  # -1 vida, inicia respawn
```

#### 2.3 Geração no mapa

Em `_matrix_to_map`, após o pipeline normal de poderes, selecionar tiles candidatos:
- Tile é floor (walkable), não é crítico, não é START/END.
- Tile tem ao menos 2 vizinhos walkables na mesma linha ou mesma coluna (garante trajeto viável).
- Probabilidade controlada por `prob_wall` no `DifficultyConfig`.

Para cada tile candidato:
```
axis, point_a, point_b = encontrar_trajeto(col, row, matrix)
# encontrar_trajeto verifica se existem N tiles contíguos walkables
# no eixo col ou no eixo row; escolhe o eixo com maior comprimento contíguo.
# point_a = extremo esquerdo/superior, point_b = extremo direito/inferior.
speed = base_speed * dificuldade_fator
bloco = MovingWallBlock(pos, axis, point_a, point_b, speed)
_moving_blocks.append(bloco)
_grid[(col, row)] = bloco  # substitui o tile normal
```

#### 2.4 Renderização

`MovingWallBlock.draw()` usa a posição visual interpolada (`self.position`) e renderiza um cubo mais alto (HEIGHT_VISUAL = 0.6) em cor cinza metálica. Como `map_.draw()` itera `_grid.values()`, o bloco é renderizado automaticamente se estiver no grid. A posição visual suave (lerp) é mantida internamente — o grid só muda em passos inteiros.

> **Problema de consistência:** o draw usa a posição visual (suave), mas o grid usa posição inteira. Isso significa que visualmente o bloco pode estar "entre" dois tiles enquanto o grid o considera em apenas um. Esta inconsistência é aceitável para a primeira implementação — o bloco bloqueia o destino antes de chegar visualmente lá, o que é ligeiramente punitivo mas previsível.

#### 2.5 Interação com can_move_to

`Map.can_move_to(col, row)` já retorna `block is not None and block.active`. Como `MovingWallBlock` terá `active=True` e estará no `_grid`, a verificação existente funciona sem modificação. O Cube não conseguirá rolar para um tile ocupado por um WallBlock — comportamento correto.

### Dependências

- Nenhuma outra melhoria é pré-requisito.
- Requer que `Map.update(dt)` exista e seja chamado no game loop. Atualmente `map_.update(dt)` já é chamado em `main.py` (linha ~352) — porém `Map.update()` precisa iterar `_moving_blocks` e chamar `block.update(dt)`.
- O callback de colisão `hit_by_wall()` precisa ser adicionado ao `Cube` — pode reutilizar a lógica existente de `_handle_fall()` (já implementada em `src/entities/cube.py`).

---

## 3. Controle de densidade e combinações de poderes

### Problema

O sistema atual (`_matrix_to_map` em `src/world/map.py`) distribui poderes por probabilidade uniforme sobre todos os tiles, usando apenas `zone` (distância normalizada do START) como contexto. Não há controle de:

- **Sequência local:** um IceBlock pode aparecer imediatamente antes de uma borda sem nenhum espaço para frear.
- **Vizinhança:** dois FragileBlocks adjacentes tornam a recuperação impossível se o cubo precisar retroceder.
- **Concentração por zona:** não existe como dizer "esta área específica deve ser dominada por IceBlocks".
- **Combos intencionais:** nenhuma sequência pré-desenhada de poderes (ex: Ice→Bounce→borda) é possível.

Referência: `GAMEDESIGN.md` seção 2.5, problema L1 (sem controle de densidade local).

### O que muda

Três adições independentes, em ordem crescente de complexidade:

#### 3.1 Regra de vizinhança anti-clustering

**O que é:** Após selecionar um poder para um tile, reduzir o peso desse mesmo poder nos N vizinhos imediatos (N=2 por padrão).

**Arquivo:** `src/world/map.py`, função `_matrix_to_map`.

**Algoritmo:**

```
recency: dict[(col, row) → {power_name: cooldown}] = {}

ao colocar power_name no tile (col, row):
    para cada vizinho (nc, nr) em raio de 2 tiles:
        recency[(nc, nr)][power_name] = COOLDOWN_STEPS  # ex: 3

ao calcular zone_weight para tile (col, row):
    se (col, row) em recency e power_name em recency[(col,row)]:
        fator = recency[(col,row)][power_name] / COOLDOWN_STEPS  # [0, 1]
        weight *= (1 - 0.7 * fator)  # reduz peso em até 70%

decrementar cooldown ao processar cada tile (ordem BFS de distância)
```

Esta abordagem não altera a assinatura de nenhuma função pública. É um estado local dentro de `_matrix_to_map`.

#### 3.2 Cluster zones (parâmetro de DifficultyConfig)

**O que é:** Um novo campo `cluster_zones` no `DifficultyConfig` — lista de tuplas que definem regiões com bias de tipo específico.

**Arquivo:** `sandboxes/menu.py` (definição), `src/world/map.py` (consumo).

**Estrutura do parâmetro:**

```python
# Em DifficultyConfig:
cluster_zones: list[tuple] = field(default_factory=list)
# Formato de cada entrada: (zone_min, zone_max, power_name, multiplier)
# Exemplo Difícil:
cluster_zones=[
    (0.55, 0.75, "ice",     2.5),   # corredor de gelo no meio-final
    (0.75, 0.90, "fragile", 2.0),   # zona frágil antes do END
    (0.30, 0.50, "bounce",  1.8),   # bounces no mid-game
]
```

**Consumo em `zone_weight`:**

```python
def zone_weight(name, base, zone, is_critical, cluster_zones):
    weight = <lógica atual>
    for (zmin, zmax, cname, mult) in cluster_zones:
        if cname == name and zmin <= zone < zmax:
            weight *= mult
            break
    return weight
```

`cluster_zones=[]` mantém comportamento idêntico ao atual — retrocompatível.

#### 3.3 Sequências de combo (combo_sequences)

**O que é:** Um novo campo `combo_sequences` no `DifficultyConfig` — lista de sequências de poderes que devem aparecer em tiles consecutivos do caminho principal.

**Arquivo:** `sandboxes/menu.py` (definição), `src/world/map.py` (consumo em `_matrix_to_map`).

**Estrutura do parâmetro:**

```python
combo_sequences: list[list[str]] = field(default_factory=list)
# Exemplo:
combo_sequences=[
    ["ice", "bounce"],          # Ice seguido de Bounce — exige antecipação
    ["invert", "fragile"],      # Inverte controles e bloco frágil embaixo
    ["slow", "checkpoint"],     # Slow seguido de checkpoint como alívio
]
```

**Algoritmo de inserção em `_matrix_to_map`:**

```
1. Após o pipeline normal, coletar os tiles do caminho crítico ordenados por distância.
2. Para cada combo_sequence definida:
   a. Selecionar aleatoriamente um ponto de inserção no caminho crítico
      (excluindo zona < 0.28 e zona > 0.88 — regras existentes de intent_allowed).
   b. Verificar que os N tiles consecutivos a partir do ponto são todos floor normais
      (não são START, END, nem já possuem poder).
   c. Substituir esses N tiles pelos poderes da sequência.
3. Aplicar no máximo 1 combo por sequência definida (evita saturação).
```

Esta etapa roda **após** o pipeline probabilístico normal, sobrescrevendo tiles selecionados. Sequências definidas têm prioridade sobre distribuição aleatória.

### Arquivos envolvidos

| Arquivo | Papel |
|---|---|
| `src/world/map.py` | Adicionar lógica de anti-clustering em `_matrix_to_map`; consumir `cluster_zones` em `zone_weight`; adicionar passo de inserção de combos após pipeline normal. |
| `sandboxes/menu.py` | Adicionar campos `cluster_zones` e `combo_sequences` ao `DifficultyConfig`; definir valores para cada dificuldade. |

### Dependências

- A regra de vizinhança (3.1) é independente e pode ser implementada sem as demais.
- `cluster_zones` (3.2) requer mudança em `DifficultyConfig` e em `zone_weight` — podem ser feitos juntos.
- `combo_sequences` (3.3) depende do caminho crítico (`critical_path`) estar disponível em `_matrix_to_map` — já está (produzido por `_path_analysis`).

---

## 4. Ocultar EndBlock e limitar campo visual

### Problema

A câmera orbital padrão (`distance=12`, `height=9`, sem fog-of-war) revela praticamente todo o mapa ao jogador desde o início. O EndBlock (bloco verde de destino) é visível logo no primeiro frame em mapas Fácil e Médio. Isso elimina:

- O elemento de descoberta e orientação espacial.
- A tensão de "qual direção é a correta?".
- A dificuldade estrutural do Difícil, que deveria exigir navegação sem rota óbvia.

Referência: `GAMEDESIGN.md` seção 1.2 ("Mapa completamente visível") e seção 4.6 (Vetor F — Fog of war parcial, F4).

### Três opções de implementação

Cada opção é independente e pode ser combinada com as demais.

---

#### Opção A — Fog of war por raio do Cube

**O que é:** Filtrar o draw do mapa — renderizar apenas tiles dentro de raio `fog_radius` (em tiles) da posição atual do Cube.

**Arquivo:** `src/world/map.py` (método `draw()`).

**Parâmetro de controle:** novo campo `fog_radius: int` no `DifficultyConfig` (0 = desativado, compatível com comportamento atual).

```python
# Valores propostos:
# Fácil:   fog_radius=0  (sem fog — tutorial não deve desorientar)
# Médio:   fog_radius=12 (revela ~12 tiles ao redor do cubo)
# Difícil: fog_radius=8  (campo visual restrito)
```

**Algoritmo em `Map.draw(cube_pos=None, fog_radius=0)`:**

```python
for (col, row), block in self._grid.items():
    if fog_radius > 0 and cube_pos is not None:
        dx = abs(col - cube_pos[0])
        dz = abs(row - cube_pos[1])
        if max(dx, dz) > fog_radius:  # distância de Chebyshev
            continue
    block.draw()
```

`main.py` passa `cube_pos=cube.get_grid_position()` e `fog_radius=difficulty.fog_radius` ao chamar `map_.draw()`.

**Impacto visual:** tiles além do raio simplesmente não aparecem — fundo vazio (cor de fundo OpenGL). O EndBlock torna-se invisível a distâncias > `fog_radius` tiles.

**Efeito colateral:** o jogador não sabe o que está além do campo visual. Pode ser desejável (tensão) ou não (frustração). Controlável por `fog_radius`.

---

#### Opção B — EndBlock disfarçado

**O que é:** O EndBlock renderiza visualmente como um tile neutro (cor de chão normal) até que o Cube esteja a menos de `reveal_distance` tiles de distância. Ao entrar no raio, a animação/cor normal do EndBlock é revelada.

**Arquivo:** `src/entities/block.py` (`EndBlock.draw()`), `src/world/map.py` (passa posição do Cube ao `draw()`).

**Parâmetro de controle:** `reveal_distance: int` em `DifficultyConfig` (0 = sempre visível, retrocompatível).

```python
class EndBlock(Block):
    def draw(self, cube_dist=None, reveal_distance=0):
        if reveal_distance > 0 and cube_dist is not None and cube_dist > reveal_distance:
            # Renderizar como tile neutro (cor padrão de Block)
            self._draw_as_neutral()
        else:
            # Renderização normal do EndBlock (verde, textura especial)
            super().draw()
```

`Map.draw()` calcula `cube_dist = distance_from_start[end_pos] - distance_from_start[cube_pos]` (diferença de distância BFS) e passa ao `EndBlock.draw()`.

**Vantagem sobre Opção A:** não esconde a estrutura geral do mapa — apenas o destino. Menos frustrante, mais cirúrgico.

---

#### Opção C — Câmera mais baixa/próxima por dificuldade

**O que é:** Reduzir `camera_distance` e `camera_height` padrões em dificuldades mais altas, estreitando o campo visual sem alterar lógica de renderização.

**Arquivo:** `sandboxes/menu.py` (novos campos em `DifficultyConfig`), `main.py` (inicializar câmera com valores da dificuldade).

**Parâmetro de controle:** novos campos `camera_distance_default` e `camera_height_default` no `DifficultyConfig`.

```python
# Valores propostos:
# Fácil:   camera_distance=14, camera_height=10  (visão ampla — facilita navegação)
# Médio:   camera_distance=10, camera_height=7   (campo reduzido)
# Difícil: camera_distance=8,  camera_height=5   (câmera baixa, visão próxima)
```

**Vantagem:** sem mudança de lógica de renderização. A câmera já tem controles de distância/altura implementados em `main.py`.

**Limitação:** não oculta o mapa — apenas reduz quanto é visível. O jogador ainda pode afastar a câmera manualmente (se os controles permitirem).

---

### Recomendação

Para primeira implementação: **Opção C** (câmera por dificuldade) + **Opção B** (EndBlock disfarçado no Difícil com `reveal_distance=15`). São as mais simples, menos intrusivas visualmente e já entregam o efeito de descoberta gradual. A Opção A (fog of war completo) pode ser adicionada depois como camada adicional.

### Arquivos envolvidos (resumo)

| Arquivo | Opção | Papel |
|---|---|---|
| `sandboxes/menu.py` | A, B, C | Novos campos `fog_radius`, `reveal_distance`, `camera_distance_default`, `camera_height_default` |
| `src/world/map.py` | A | Filtro de raio em `Map.draw()` |
| `src/entities/block.py` | B | `EndBlock.draw()` com modo disfarçado |
| `main.py` | B, C | Passar parâmetros ao `map_.draw()` e inicializar câmera com valores da dificuldade |

### Dependências

Nenhuma outra melhoria é pré-requisito. As três opções são independentes entre si.

---

## 5. Ajustes nos poderes dos blocos existentes

### Problema

Os 10 poderes existentes têm desequilíbrios identificados em `GAMEDESIGN.md` (seções 3.1 e 4.5):

- **ShrinkBlock** é permanente sem utilidade tática real — encolher apenas reduz o step, não abre novas rotas.
- **CheckpointBlock** é passivo e coletado sem escolha consciente.
- **PortalBlock** é aleatório demais — deposita o cubo em posição completamente imprevisível, incluindo void.
- **InvertBlock** inverte os controles por 5s sem nenhum feedback visual do tempo restante.
- **FragileBlock** desaparece mas raramente tem impacto real porque o respawn recoloca o cubo antes do bloco frágil.

### Ajuste A — ShrinkBlock: tiles small-only

**O que muda:** Introduzir um novo tipo de tile, `NarrowPassageBlock`, que só pode ser atravessado pelo cubo no estado encolhido (`scale == 0.5`). Para o cubo normal, comporta-se como WallBlock (impassável).

**Arquivos:**

| Arquivo | Papel |
|---|---|
| `src/entities/block.py` | Nova subclasse `NarrowPassageBlock` com `is_narrow=True`. |
| `src/world/map.py` | `can_move_to` verifica `block.is_narrow` e tamanho atual do cubo antes de permitir movimento. Geração: inserir `NarrowPassageBlock` no gerador como tipo de tile com `prob_narrow` controlado por `DifficultyConfig`. |
| `sandboxes/menu.py` | Novo campo `prob_narrow` em `DifficultyConfig`. |

**Algoritmo em `can_move_to`:**

```python
def can_move_to(self, col, row, cube_scale=1.0):
    block = self._grid.get((col, row))
    if block is None or not block.active:
        return False
    if getattr(block, 'is_narrow', False) and cube_scale > 0.5:
        return False  # cubo normal não passa por passagem estreita
    return True
```

O `Cube` já conhece seu `scale` atual — passa como argumento ao chamar `map_.can_move_to()`.

**Efeito de game design:** ShrinkBlock passa a ser uma vantagem tática além de um obstáculo permanente. O jogador encolhido pode tomar rotas alternativas inacessíveis ao cubo normal. Combinado com `GrowBlock` no final da passagem estreita, cria um ciclo de decisão consciente.

---

### Ajuste B — CheckpointBlock: ativação opcional e usos limitados

**O que muda:** O CheckpointBlock não ativa automaticamente ao ser pisado. O jogador precisa pressionar uma tecla de ação (`E` ou `Space`) estando sobre o tile para ativá-lo. Opcionalmente, limitar a 2 usos (respawns) antes de o checkpoint expirar.

**Arquivos:**

| Arquivo | Papel |
|---|---|
| `src/entities/cube.py` | Adicionar ação `try_activate_checkpoint()` no input handling; Cube verifica se está sobre um `CheckpointBlock` e chama `map_.activate_checkpoint(pos)`. |
| `src/entities/block.py` | `CheckpointBlock` ganha campo `uses_remaining: int` (default 2). A cada respawn a partir deste checkpoint, `uses_remaining -= 1`; quando chega a 0, o checkpoint expira (`active=False`, ou cor/estado visual muda). |
| `main.py` | Adicionar mapeamento da tecla de ação (`E`) para `cube.try_activate_checkpoint()`. |

**Efeito de game design:** O jogador precisa decidir conscientemente quando salvar. Um checkpoint com 2 usos cria custo de oportunidade — usar cedo pode desperdiçar o slot para uma zona mais difícil à frente.

---

### Ajuste C — PortalBlock: pares determinísticos

**O que muda:** Em vez de teleportar para posição aleatória, portais existem em pares ligados. Portal A leva ao Portal B; Portal B leva ao Portal A. A ligação é visual (linha de partículas ou simplesmente cor compartilhada entre o par).

**Arquivos:**

| Arquivo | Papel |
|---|---|
| `src/entities/block.py` | `PortalBlock` ganha campo `linked_pos: tuple[int,int]` — posição do portal destino. |
| `src/world/map.py` | `_matrix_to_map` cria portais em pares: seleciona dois tiles candidatos, cria dois `PortalBlock` apontando um para o outro. Atualizar `_apply_portal` (ou equivalente no Map) para usar `linked_pos` em vez de posição aleatória. |
| `src/entities/cube.py` | `_handle_portal()` já chama `map_.get_portal_destination(pos)` (ou equivalente). Substituir lógica aleatória por lookup de `linked_pos`. |

**Algoritmo de geração de pares:**

```
portal_candidates = [tiles não-críticos, zona > 0.30, não adjacentes a borda]
embaralhar portal_candidates
para cada par (tile_a, tile_b) em portal_candidates[::2]:
    criar PortalBlock(tile_a, linked_pos=tile_b)
    criar PortalBlock(tile_b, linked_pos=tile_a)
    _grid[tile_a] = portal_a
    _grid[tile_b] = portal_b
```

**Efeito de game design:** O jogador pode explorar e memorizar os pares de portais. Portais tornam-se atalhos táticos ou armadilhas conhecidas, não roletas aleatórias.

---

### Ajuste D — InvertBlock: timer visual no HUD

**O que muda:** Adicionar um indicador visual na HUD que mostra o tempo restante do efeito de inversão (e de outros efeitos com duração, como SlowBlock).

**Arquivos:**

| Arquivo | Papel |
|---|---|
| `src/entities/cube.py` | Expor propriedade `active_effects: list[dict]` com nome do efeito e `time_remaining`. InvertBlock já tem `_invert_remaining` (float); SlowBlock tem `_slow_remaining`. Centralizar em `active_effects`. |
| `main.py` | Na seção de HUD (projeção ortogonal), renderizar ícone + barra de progresso para cada efeito em `cube.active_effects`. Usar `glDrawPixels` ou `GL_QUADS` com cor proporcional ao tempo restante. |

**Estrutura de `active_effects`:**

```python
@property
def active_effects(self) -> list[dict]:
    effects = []
    if self._invert_remaining > 0:
        effects.append({"name": "invert", "remaining": self._invert_remaining, "max": 5.0})
    if self._slow_remaining > 0:
        effects.append({"name": "slow", "remaining": self._slow_remaining, "max": ...})
    return effects
```

**Efeito de game design:** O jogador sabe exatamente quando o controle voltará ao normal, transformando InvertBlock de surpresa frustrante em desafio gerenciável com countdown.

---

### Ajuste E — FragileBlock: destruição em cadeia com Checkpoint

**O que muda:** Se um `CheckpointBlock` ativo estiver adjacente (vizinho de 1 tile) a um `FragileBlock` que acabou de deativar, o `CheckpointBlock` adjacente também se desativa.

**Arquivos:**

| Arquivo | Papel |
|---|---|
| `src/world/map.py` | Método `schedule_fragile(pos)` (já existente) — ao desativar um FragileBlock, verificar vizinhos; se encontrar `CheckpointBlock` ativo, chamar `checkpoint.deactivate()`. |
| `src/entities/block.py` | `CheckpointBlock` ganha método `deactivate()` que muda `is_active_checkpoint=False` e `active=False` com animação de blink (reusando a lógica de blink existente no `FragileBlock`). |

**Efeito de game design:** Cria interação emergente entre dois sistemas existentes — o jogador precisa pensar se vale a pena ativar um checkpoint perto de tiles frágeis. Adiciona profundidade sem criar novos blocos.

---

### Resumo dos ajustes — impacto × esforço

| Ajuste | Impacto de Game Design | Esforço de Impl. | Dependência |
|---|---|---|---|
| A — ShrinkBlock small-only | Alto — Shrink vira mecânica tática | Médio (novo tipo de tile + mudança em can_move_to) | Seção 1 (prob_narrow no DifficultyConfig) |
| B — Checkpoint opcional/limitado | Médio — adiciona escolha consciente | Baixo (nova tecla + contador) | Nenhuma |
| C — Portal determinístico | Alto — remove aleatoriedade punitiva | Médio (lógica de par + geração) | Nenhuma |
| D — Timer HUD de efeitos | Médio — melhora legibilidade | Baixo (HUD existente + nova propriedade) | Nenhuma |
| E — FragileBlock destrói Checkpoint | Médio — emergência entre sistemas | Baixo (3-5 linhas em schedule_fragile) | Nenhuma |

---

## Ordem de implementação recomendada

Com base na relação impacto/esforço e dependências:

1. **Seção 1** — Rebalancear DifficultyConfig. Zero código, máximo impacto imediato. Testar com `sandbox_map.py` para verificar a forma dos novos mapas.
2. **Seção 5-D** — Timer HUD de efeitos. Baixo esforço, melhora legibilidade de todas as sessões de jogo seguintes.
3. **Seção 5-E** — FragileBlock destrói Checkpoint. Três linhas de código, cria interação emergente.
4. **Seção 4 (Opção C + B)** — Câmera por dificuldade + EndBlock disfarçado. Impacto alto no Difícil, baixo esforço.
5. **Seção 5-C** — Portal determinístico. Remove o único poder com aleatoriedade punitiva.
6. **Seção 3.1** — Regra de vizinhança anti-clustering. Melhora distribuição sem nova UI.
7. **Seção 2** — WallBlock dinâmico. A mais complexa — requer novo ciclo de vida no Map.
8. **Seção 5-A** — ShrinkBlock small-only + NarrowPassageBlock. Depende do gerador suportar novo tipo.
9. **Seção 3.2 + 3.3** — cluster_zones e combo_sequences. Requer mais testes de balanceamento.

---

*Documento criado em 2026-05-23. Atualizar conforme melhorias forem sendo implementadas.*
