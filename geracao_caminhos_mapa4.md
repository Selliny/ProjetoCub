# Geração de múltiplos caminhos — Sistema do Mapa 4 (Loop Central)

> Algoritmo completo para geração procedural de mapas com caminhos de **1 tile de largura**,
> baseado na arquitetura de **loop central com entrada e saída separadas**.

---

## 1. Conceito do sistema

O Mapa 4 é construído sobre uma ideia central: o caminho **entra**, **circula por um anel**,
e **sai por um ponto diferente da entrada**. Isso cria naturalmente dois arcos internos —
um superior e um inferior — que podem ser explorados como caminhos alternativos.

```
........................
........................
....###############.....   ← arco superior do anel
....#.............#.....
....#.............#.....
S######...........#####.   ← entrada esquerda → saída direita
......#...........#...#.
......#...........#...#.
......#...........#...#.
......#############...#.   ← arco inferior do anel
...................E###.
........................
```

**Componentes fixos da arquitetura:**

| Componente | Descrição |
|---|---|
| Corredor de entrada | Segmento linear de `START` até o anel |
| Anel (loop) | Estrutura fechada com arco superior e arco inferior |
| Ponto de bifurcação | Célula onde o caminho se divide em dois arcos |
| Ponto de convergência | Célula onde os dois arcos se reencontram |
| Corredor de saída | Segmento linear do anel até `END` |

---

## 2. Estrutura de dados

### 2.1 Representação da grade

```python
TILE_GRAMA  = 0   # área bloqueada (gramado)
TILE_CAMINHO = 1  # tile transitável (terra)
TILE_START  = 2   # ponto inicial do cubo
TILE_END    = 3   # ponto final
TILE_BIFURC = 4   # marcador interno: ponto de divisão de caminho
TILE_CONVERG = 5  # marcador interno: ponto de reunião de caminho

# Grade bidimensional
grid[row][col]   # acesso padrão
```

### 2.2 Descrição de um caminho

Cada caminho é uma lista ordenada de células `(row, col)` do `START` ao `END`:

```python
Caminho = list[tuple[int, int]]

# Exemplo de estrutura de saída do gerador
{
    "grid":     grid,          # grade 2D final
    "caminhos": [              # lista de caminhos alternativos
        [(5,0),(5,1),...],     # caminho A — arco superior
        [(5,0),(5,1),...],     # caminho B — arco inferior
    ],
    "start":    (5, 0),
    "end":      (10, 19),
    "bifurcacao":   (5, 5),   # ponto de divisão
    "convergencia": (5, 18),  # ponto de reunião
}
```

---

## 3. Parâmetros de geração

```python
@dataclass
class ParametrosMapa4:
    largura:      int   = 24      # colunas da grade
    altura:       int   = 12      # linhas da grade
    seed:         int   = None    # semente para reprodutibilidade

    # Corredor de entrada (START → anel)
    entrada_row:  int   = None    # linha do corredor de entrada (padrão: altura//2 - 1)
    entrada_len:  int   = None    # comprimento em tiles (padrão: largura//6)

    # Anel
    anel_margem_esq:   int = None # distância da borda esq até o anel (padrão: entrada_len + 1)
    anel_margem_dir:   int = None # distância da borda dir até o anel (padrão: largura//6)
    anel_margem_topo:  int = None # distância do topo até o anel     (padrão: altura//5)
    anel_margem_base:  int = None # distância da base até o anel     (padrão: altura//4)

    # Corredor interno (cria bifurcação)
    corredor_interno_row:  int = None  # linha do corredor que corta o anel
    corredor_interno_len:  int = None  # largura do corredor interno

    # Corredor de saída (anel → END)
    saida_row:    int   = None    # linha do corredor de saída
    saida_len:    int   = None    # comprimento em tiles

    # Variações de caminhos
    n_caminhos:   int   = 2       # 2 = padrão (arco sup + arco inf)
                                  # 3 = adiciona corredor diagonal interno
                                  # 4 = adiciona atalho central

    # Geração aleatória
    ruido_arcos:  float = 0.0     # 0.0 = arcos retos | 0.3 = leve ondulação | 1.0 = drunkard walk
```

---

## 4. Algoritmo principal

### 4.1 Pseudocódigo completo

```
FUNÇÃO gerar_mapa4(params):

  ── FASE 1: Inicialização ──────────────────────────────────────────
  rng   ← RNG(params.seed)
  grid  ← grade(params.largura, params.altura) preenchida com TILE_GRAMA
  preencher_defaults(params, rng)        // calcula valores omitidos

  ── FASE 2: Calcular geometria do anel ────────────────────────────
  anel ← {
    topo:  params.anel_margem_topo,
    base:  params.altura - params.anel_margem_base - 1,
    esq:   params.anel_margem_esq,
    dir:   params.largura - params.anel_margem_dir - 1,
  }

  bifurcacao   ← (params.entrada_row, anel.esq)       // canto esq do anel na linha de entrada
  convergencia ← (params.saida_row,   anel.dir)       // canto dir do anel na linha de saída

  ── FASE 3: Escavar corredor de entrada ───────────────────────────
  start ← (params.entrada_row, 0)
  escavar_horizontal(grid, start, params.entrada_len, direção=DIREITA)
  grid[start] ← TILE_START

  ── FASE 4: Escavar o anel ────────────────────────────────────────
  // Borda superior
  escavar_horizontal(grid, (anel.topo, anel.esq), anel.dir - anel.esq + 1)
  // Borda inferior
  escavar_horizontal(grid, (anel.base, anel.esq), anel.dir - anel.esq + 1)
  // Borda esquerda
  escavar_vertical(grid, (anel.topo, anel.esq), anel.base - anel.topo + 1)
  // Borda direita
  escavar_vertical(grid, (anel.topo, anel.dir), anel.base - anel.topo + 1)

  // Marca ponto de bifurcação e convergência
  grid[bifurcacao]   ← TILE_BIFURC
  grid[convergencia] ← TILE_CONVERG

  ── FASE 5: Escavar corredor de saída ─────────────────────────────
  end ← (params.saida_row, params.largura - 1 - params.saida_len)
  escavar_horizontal(grid, convergencia, params.saida_len + 1, direção=DIREITA)
  grid[end] ← TILE_END

  ── FASE 6: Escavar caminhos alternativos ─────────────────────────
  caminhos ← []

  // Caminho A — arco superior (sempre presente)
  camA ← tracar_arco_superior(grid, anel, bifurcacao, convergencia, params.ruido_arcos, rng)
  caminhos.append(camA)

  // Caminho B — arco inferior (sempre presente)
  camB ← tracar_arco_inferior(grid, anel, bifurcacao, convergencia, params.ruido_arcos, rng)
  caminhos.append(camB)

  SE params.n_caminhos >= 3:
    // Caminho C — corredor interno diagonal
    camC ← tracar_corredor_interno(grid, anel, params, rng)
    caminhos.append(camC)

  SE params.n_caminhos >= 4:
    // Caminho D — atalho central (corta o anel pelo meio)
    camD ← tracar_atalho_central(grid, anel, bifurcacao, convergencia, rng)
    caminhos.append(camD)

  ── FASE 7: Montar caminhos completos (entrada + arco + saída) ────
  prefixo ← caminho de start até bifurcacao (corredor de entrada)
  sufixo  ← caminho de convergencia até end (corredor de saída)

  caminhos_completos ← [prefixo + cam + sufixo PARA cam EM caminhos]

  ── FASE 8: Verificação final ─────────────────────────────────────
  PARA CADA caminho EM caminhos_completos:
    SE NÃO bfs_verifica(grid, start, end, caminho):
      LANÇAR ErroDeConectividade(caminho)

  RETORNAR {
    grid, caminhos: caminhos_completos,
    start, end, bifurcacao, convergencia,
  }
```

---

### 4.2 Preenchimento de defaults

```python
def preencher_defaults(p: ParametrosMapa4, rng):
    p.entrada_row = p.entrada_row or p.altura // 2 - 1
    p.entrada_len = p.entrada_len or max(2, p.largura // 6)

    p.anel_margem_esq  = p.anel_margem_esq  or p.entrada_len + 1
    p.anel_margem_dir  = p.anel_margem_dir  or max(3, p.largura // 6)
    p.anel_margem_topo = p.anel_margem_topo or max(1, p.altura // 5)
    p.anel_margem_base = p.anel_margem_base or max(2, p.altura // 4)

    p.saida_row = p.saida_row or p.entrada_row + 2   # linha de saída ligeiramente abaixo
    p.saida_len = p.saida_len or max(2, p.largura // 7)

    # garante que saída está dentro dos limites do anel
    anel_base = p.altura - p.anel_margem_base - 1
    if p.saida_row > anel_base:
        p.saida_row = anel_base
```

---

### 4.3 Traçado do arco superior

O arco superior conecta `bifurcacao` ao topo do anel, percorre a borda superior e desce até `convergencia`.

```python
def tracar_arco_superior(grid, anel, bifurcacao, convergencia, ruido, rng) -> Caminho:
    caminho = []
    r_bif, c_bif = bifurcacao
    r_con, c_con = convergencia

    # Sobe da bifurcação até o topo do anel
    for r in range(r_bif, anel['topo'] - 1, -1):
        caminho.append((r, c_bif))
        grid[r][c_bif] = TILE_CAMINHO

    # Percorre a borda superior da esquerda para a direita
    for c in range(c_bif, c_con + 1):
        pos = (anel['topo'], c)
        if ruido > 0:
            pos = aplicar_ruido(pos, grid, anel, ruido, rng)
        caminho.append(pos)
        grid[pos[0]][pos[1]] = TILE_CAMINHO

    # Desce do topo até a convergência
    for r in range(anel['topo'], r_con + 1):
        caminho.append((r, c_con))
        grid[r][c_con] = TILE_CAMINHO

    return caminho
```

---

### 4.4 Traçado do arco inferior

Espelho do arco superior: desce até a base do anel, percorre a borda inferior, e sobe até `convergencia`.

```python
def tracar_arco_inferior(grid, anel, bifurcacao, convergencia, ruido, rng) -> Caminho:
    caminho = []
    r_bif, c_bif = bifurcacao
    r_con, c_con = convergencia

    # Desce da bifurcação até a base do anel
    for r in range(r_bif, anel['base'] + 1):
        caminho.append((r, c_bif))
        grid[r][c_bif] = TILE_CAMINHO

    # Percorre a borda inferior da esquerda para a direita
    for c in range(c_bif, c_con + 1):
        pos = (anel['base'], c)
        if ruido > 0:
            pos = aplicar_ruido(pos, grid, anel, ruido, rng)
        caminho.append(pos)
        grid[pos[0]][pos[1]] = TILE_CAMINHO

    # Sobe da base até a convergência
    for r in range(anel['base'], r_con - 1, -1):
        caminho.append((r, c_con))
        grid[r][c_con] = TILE_CAMINHO

    return caminho
```

---

### 4.5 Corredor interno (3º caminho)

Corta o anel pelo meio, criando um atalho diagonal em L que não toca as bordas do anel.

```python
def tracar_corredor_interno(grid, anel, params, rng) -> Caminho:
    """
    Traça um corredor dentro do anel, de bifurcacao até convergencia,
    passando pelo interior (sem usar as bordas do anel).

    Estratégia: anda horizontalmente pelo meio do anel,
    depois faz uma inflexão vertical para chegar na linha de convergência.
    """
    r_bif, c_bif = params.bifurcacao
    r_con, c_con = params.convergencia

    # Linha do corredor interno: média entre topo e base do anel
    r_meio = (anel['topo'] + anel['base']) // 2

    # Adiciona variação aleatória pequena para naturalidade
    variacao = rng.randint(-1, 1)
    r_meio = max(anel['topo'] + 1, min(anel['base'] - 1, r_meio + variacao))

    caminho = []

    # Da bifurcação, move para a linha do meio (vertical)
    passo = 1 if r_meio > r_bif else -1
    for r in range(r_bif, r_meio + passo, passo):
        caminho.append((r, c_bif))
        grid[r][c_bif] = TILE_CAMINHO

    # Percorre horizontalmente até a coluna de convergência
    for c in range(c_bif, c_con + 1):
        caminho.append((r_meio, c))
        grid[r_meio][c] = TILE_CAMINHO

    # Sobe/desce até a linha de convergência (vertical)
    passo = 1 if r_con > r_meio else -1
    for r in range(r_meio, r_con + passo, passo):
        caminho.append((r, c_con))
        grid[r][c_con] = TILE_CAMINHO

    return caminho
```

---

### 4.6 Atalho central (4º caminho)

Corta diagonalmente em dois L's, partindo do centro geométrico do anel.

```python
def tracar_atalho_central(grid, anel, bifurcacao, convergencia, rng) -> Caminho:
    """
    Cria um atalho em X dentro do anel:
    bifurcacao → centro do anel → convergencia

    Útil como bônus/penalidade — o caminho mais curto pode ser
    o mais perigoso (blocos de dano concentrados aqui).
    """
    r_bif, c_bif = bifurcacao
    r_con, c_con = convergencia

    # Centro do anel
    r_cent = (anel['topo'] + anel['base']) // 2
    c_cent = (anel['esq']  + anel['dir'])  // 2

    caminho = []

    # Bifurcação → centro (L invertido)
    passo_r = 1 if r_cent > r_bif else -1
    for r in range(r_bif, r_cent + passo_r, passo_r):
        caminho.append((r, c_bif))
        grid[r][c_bif] = TILE_CAMINHO

    for c in range(c_bif, c_cent + 1):
        caminho.append((r_cent, c))
        grid[r_cent][c] = TILE_CAMINHO

    # Centro → convergência (L normal)
    for c in range(c_cent, c_con + 1):
        caminho.append((r_cent, c))
        grid[r_cent][c] = TILE_CAMINHO

    passo_r = 1 if r_con > r_cent else -1
    for r in range(r_cent, r_con + passo_r, passo_r):
        caminho.append((r, c_con))
        grid[r][c_con] = TILE_CAMINHO

    # Remove duplicatas mantendo ordem
    seen = set()
    caminho = [p for p in caminho if not (p in seen or seen.add(p))]

    return caminho
```

---

### 4.7 Ruído nos arcos (variação orgânica)

Quando `ruido_arcos > 0`, cada tile ao longo da borda do anel tem chance de desviar
1 célula para dentro do anel, criando um efeito de caminho irregular:

```python
def aplicar_ruido(pos, grid, anel, fator, rng) -> tuple[int, int]:
    """
    Desvia o tile 1 célula para dentro do anel com probabilidade = fator.
    Nunca desviar para fora dos limites do anel.
    """
    r, c = pos

    if rng.random() > fator:
        return pos  # sem desvio

    # Determina direção do desvio (sempre para interior)
    if r == anel['topo']:
        candidato = (r + 1, c)  # desce (para dentro)
    elif r == anel['base']:
        candidato = (r - 1, c)  # sobe (para dentro)
    elif c == anel['esq']:
        candidato = (r, c + 1)  # vai pra direita (para dentro)
    elif c == anel['dir']:
        candidato = (r, c - 1)  # vai pra esquerda (para dentro)
    else:
        return pos

    nr, nc = candidato
    # Verifica se não colide com outra célula de caminho existente
    if grid[nr][nc] == TILE_GRAMA:
        return candidato

    return pos
```

---

## 5. Variações de layout

### Variação A — 2 caminhos (padrão)

```
S####..........#####
.....#.........#...#
.....#.........#...#
.....#.........#...E
.....###########
```

- Arco superior (mais curto, mais direto)
- Arco inferior (mais longo, mais exposto)
- Bifurcação e convergência únicas

**Parâmetros:** `n_caminhos=2, ruido_arcos=0.0`

---

### Variação B — 3 caminhos (corredor interno)

```
S####..........#####
.....#....C....#...#
.....#...CCC...#...#
.....#....C....#...E
.....###########
```

`C` = corredor interno (3º caminho)

- Adiciona um caminho pelo interior do anel
- Mais curto que ambos os arcos — ideal para esconder blocos especiais raros
- Tensão: o jogador precisa escolher entre segurança (arcos) e atalho (interior)

**Parâmetros:** `n_caminhos=3, ruido_arcos=0.1`

---

### Variação C — 4 caminhos (atalho central em X)

```
S####..........#####
.....#...X.....#...#
.....#..XXX....#...#
.....#...X.....#...E
.....###########
```

`X` = atalho central (4º caminho)

- Quatro rotas distintas do START ao END
- O atalho central é o mais curto de todos, mas passa pelo centro do anel
- Ideal para jogos com sistema de risco/recompensa: menos tiles = menos coletas, mas menos perigos

**Parâmetros:** `n_caminhos=4, ruido_arcos=0.2`

---

### Variação D — Anel duplo (dois loops encadeados)

Dois anéis sequenciais compartilhando a coluna de convergência/bifurcação do segundo:

```
S####....####..........####....#####
.....#...#..#..........#..#....#...#
.....#...#..#..........#..#....#...E
.....#####..##############..####
```

**Implementação:** chamar `gerar_mapa4` duas vezes e conectar o `END` do primeiro
ao `START` do segundo via corredor horizontal:

```python
def gerar_mapa_duplo(params1, params2):
    mapa_a = gerar_mapa4(params1)
    params2.entrada_col_offset = mapa_a['end'][1] + 1  # continua do end do primeiro
    mapa_b = gerar_mapa4(params2)
    return mesclar_grids(mapa_a, mapa_b)
```

---

## 6. Estratégia de posicionamento de blocos de ação

Com os caminhos definidos, os blocos de ação se encaixam em **zonas funcionais**:

### Zonas e intenção de design

| Zona | Onde | Caminhos que passam | Intenção |
|---|---|---|---|
| Corredor de entrada | tiles antes da bifurcação | todos | Tutorial / bônus inicial |
| Bifurcação | tile exato da divisão | todos | Não usar bloco aqui (confunde) |
| Arco superior | borda topo do anel | só A | Blocos de coleta, menos risco |
| Arco inferior | borda base do anel | só B | Blocos de dano, maior tensão |
| Corredor interno | interior do anel | só C | Blocos raros / especiais |
| Atalho central | diagonal interna | só D | Blocos de risco alto / recompensa alta |
| Convergência | tile exato da reunião | todos | Não usar bloco aqui |
| Corredor de saída | tiles após convergência | todos | Blocos de score final / checkpoint |

### Regra de densidade por zona

```python
def calcular_densidade_blocos(caminho, zona):
    tamanho = len(caminho)
    densidades = {
        'entrada':      (1, max(1, tamanho // 4)),   # min 1, max 25%
        'arco_longo':   (2, max(2, tamanho // 3)),   # mais espaço = mais blocos
        'arco_curto':   (1, max(1, tamanho // 5)),   # menos espaço = menos blocos
        'corredor_int': (1, 2),                       # raro por definição
        'atalho':       (1, 3),                       # poucos mas impactantes
        'saida':        (1, 2),                       # 1-2 blocos finais
    }
    return densidades.get(zona, (1, 2))
```

### Distância mínima entre blocos

Para evitar que o jogador seja "punido" sem chance de reação:

```python
DISTANCIA_MINIMA_ENTRE_BLOCOS = 3   # tiles
DISTANCIA_MINIMA_APOS_BIFURCACAO = 2
DISTANCIA_MINIMA_ANTES_CONVERGENCIA = 2
```

---

## 7. Implementação de referência completa (Python)

```python
import random
from dataclasses import dataclass, field
from collections import deque
from typing import Optional

GRAMA   = 0
CAMINHO = 1
START   = 2
END     = 3

@dataclass
class Params:
    largura: int = 24
    altura:  int = 12
    seed:    Optional[int] = None
    n_caminhos:  int   = 2
    ruido_arcos: float = 0.0

def gerar_mapa4(p: Params) -> dict:
    rng = random.Random(p.seed)

    # Geometria derivada
    entrada_row = p.altura // 2 - 1
    entrada_len = max(2, p.largura // 6)
    saida_row   = entrada_row + 2

    anel = {
        'topo': max(1, p.altura // 5),
        'base': p.altura - max(2, p.altura // 4) - 1,
        'esq':  entrada_len + 1,
        'dir':  p.largura - max(3, p.largura // 6) - 1,
    }

    grid = [[GRAMA] * p.largura for _ in range(p.altura)]

    # START e corredor de entrada
    grid[entrada_row][0] = START
    for c in range(1, entrada_len + 1):
        grid[entrada_row][c] = CAMINHO

    # Anel
    for c in range(anel['esq'], anel['dir'] + 1):
        grid[anel['topo']][c] = CAMINHO
        grid[anel['base']][c] = CAMINHO
    for r in range(anel['topo'], anel['base'] + 1):
        grid[r][anel['esq']] = CAMINHO
        grid[r][anel['dir']] = CAMINHO

    bif = (entrada_row, anel['esq'])
    con = (saida_row,   anel['dir'])

    # END e corredor de saída
    saida_len = max(2, p.largura // 7)
    end_col = anel['dir'] + saida_len
    for c in range(anel['dir'], end_col + 1):
        grid[saida_row][c] = CAMINHO
    grid[saida_row][end_col] = END

    # Prefixo (start → bif) e sufixo (con → end)
    prefixo = [(entrada_row, c) for c in range(0, bif[1] + 1)]
    sufixo  = [(saida_row,   c) for c in range(con[1], end_col + 1)]

    caminhos = []

    # Arco superior
    arco_sup = []
    for r in range(bif[0], anel['topo'] - 1, -1):
        arco_sup.append((r, bif[1]))
        grid[r][bif[1]] = CAMINHO
    for c in range(bif[1], con[1] + 1):
        arco_sup.append((anel['topo'], c))
        grid[anel['topo']][c] = CAMINHO
    for r in range(anel['topo'], con[0] + 1):
        arco_sup.append((r, con[1]))
        grid[r][con[1]] = CAMINHO
    caminhos.append(prefixo + arco_sup + sufixo)

    # Arco inferior
    arco_inf = []
    for r in range(bif[0], anel['base'] + 1):
        arco_inf.append((r, bif[1]))
        grid[r][bif[1]] = CAMINHO
    for c in range(bif[1], con[1] + 1):
        arco_inf.append((anel['base'], c))
        grid[anel['base']][c] = CAMINHO
    for r in range(anel['base'], con[0] - 1, -1):
        arco_inf.append((r, con[1]))
        grid[r][con[1]] = CAMINHO
    caminhos.append(prefixo + arco_inf + sufixo)

    # Corredor interno (3º caminho)
    if p.n_caminhos >= 3:
        r_meio = (anel['topo'] + anel['base']) // 2 + rng.randint(-1, 1)
        r_meio = max(anel['topo'] + 1, min(anel['base'] - 1, r_meio))
        corr = []
        for r in range(bif[0], r_meio + 1):
            corr.append((r, bif[1]))
            grid[r][bif[1]] = CAMINHO
        for c in range(bif[1], con[1] + 1):
            corr.append((r_meio, c))
            grid[r_meio][c] = CAMINHO
        for r in range(r_meio, con[0] - 1, -1):
            corr.append((r, con[1]))
            grid[r][con[1]] = CAMINHO
        seen = set()
        corr = [x for x in corr if not (x in seen or seen.add(x))]
        caminhos.append(prefixo + corr + sufixo)

    # Atalho central (4º caminho)
    if p.n_caminhos >= 4:
        r_c = (anel['topo'] + anel['base']) // 2
        c_c = (anel['esq']  + anel['dir'])  // 2
        atl = []
        for r in range(bif[0], r_c + 1):
            atl.append((r, bif[1]))
            grid[r][bif[1]] = CAMINHO
        for c in range(bif[1], c_c + 1):
            atl.append((r_c, c))
            grid[r_c][c] = CAMINHO
        for c in range(c_c, con[1] + 1):
            atl.append((r_c, c))
            grid[r_c][c] = CAMINHO
        for r in range(r_c, con[0] - 1, -1):
            atl.append((r, con[1]))
            grid[r][con[1]] = CAMINHO
        seen = set()
        atl = [x for x in atl if not (x in seen or seen.add(x))]
        caminhos.append(prefixo + atl + sufixo)

    return {
        'grid':         grid,
        'caminhos':     caminhos,
        'start':        (entrada_row, 0),
        'end':          (saida_row, end_col),
        'bifurcacao':   bif,
        'convergencia': con,
        'anel':         anel,
    }


def imprimir_mapa(resultado):
    grid = [row[:] for row in resultado['grid']]
    r_s, c_s = resultado['start']
    r_e, c_e = resultado['end']
    grid[r_s][c_s] = START
    grid[r_e][c_e] = END

    simbolos = {GRAMA: '.', CAMINHO: '#', START: 'S', END: 'E'}
    for row in grid:
        print(''.join(simbolos[t] for t in row))


# Exemplo de uso
if __name__ == '__main__':
    for n in [2, 3, 4]:
        print(f'\n=== {n} caminho(s) ===')
        resultado = gerar_mapa4(Params(seed=42, n_caminhos=n))
        imprimir_mapa(resultado)
        for i, cam in enumerate(resultado['caminhos']):
            print(f'  Caminho {i+1}: {len(cam)} tiles')
```

---

## 8. Saída esperada do algoritmo

### 2 caminhos (`seed=42`)

```
........................
........................
.....###############....
.....#.............#....
.....#.............#....
S#####.............#....
.....#.............#....
.....#.............###E.
.....###############....
........................
........................
........................

Caminho 1 (arco superior): 35 tiles
Caminho 2 (arco inferior): 31 tiles
```

### 3 caminhos (`seed=42`)

```
........................
........................
.....###############....
.....#.............#....
.....#.............#....
S#####.............#....
.....###############....   ← corredor interno (row 6)
.....#.............###E.
.....###############....
........................
........................
........................

Caminho 1 (arco superior):   35 tiles
Caminho 2 (arco inferior):   31 tiles
Caminho 3 (corredor interno): 26 tiles
```

### 4 caminhos (`seed=42`)

```
........................
........................
.....###############....
.....#.............#....
.....#.............#....
S###################....   ← atalho central (row 5)
.....###############....
.....#.............###E.
.....###############....
........................
........................
........................

Caminho 1 (arco superior):  35 tiles
Caminho 2 (arco inferior):  31 tiles
Caminho 3 (corredor interno): 26 tiles
Caminho 4 (atalho central): 25 tiles
```

---

## 9. Tabela de comprimentos e design de dificuldade

| Caminho | Tiles típicos | Tipo de experiência |
|---|---|---|
| Arco superior | 35–45 | Padrão — maior visibilidade do mapa |
| Arco inferior | 42–55 | Mais longo — mais exposição a blocos |
| Corredor interno | 25–35 | Atalho — menos tiles mas mais denso |
| Atalho central | 18–28 | Mínimo — alta concentração de blocos |

**Princípio de design:** o caminho mais curto deve ter a maior densidade de blocos de ação negativos (dano, obstáculos). O mais longo deve ter mais blocos positivos (coleta, bônus) distribuídos. Isso cria decisão genuína para o jogador.

---

*Documento gerado como referência de implementação para o sistema de geração procedural do Cubo Runner — maio de 2026*
