# Game Design — ProjetoCub

**Versão do documento:** 0.2 (2026-05-23 — complementado com análise de geração de mapas)  
**Branch:** `main` | Commit base: `6425910`

> Este documento é vivo. Cada seção registra o estado atual e, separadamente, análises e propostas de melhoria. A implementação não é obrigação — o objetivo é acumular percepções e tomar decisões informadas.

---

## 1. Estado Atual da Jogabilidade

### 1.1 O que existe hoje

O jogo é um **puzzle de navegação por grade**: o jogador controla um cubo que rola célula a célula sobre uma plataforma suspensa no vazio. A progressão tem três fases de dificuldade (Fácil → Médio → Difícil), cada uma gerando um mapa novo proceduralmente.

**Fontes de tensão ativas:**

| Fonte | Como funciona | Frequência |
|---|---|---|
| Borda do mapa | Cair no vazio tira 1 vida | Sempre presente |
| FragileBlock | Bloco desaparece 1.5s após pisar | ~3% dos tiles (base) |
| IceBlock | Desliza automaticamente 3 casas sem controle | ~3% dos tiles (base) |
| SlowBlock | Rolls 2× mais lentos por 3 movimentos | ~1.5% dos tiles (base) |
| InvertBlock | WASD invertido por 5s | ~2% dos tiles (base) |
| BounceBlock | Teleporta 2 casas à frente, pode cair | ~1.8% dos tiles (base) |
| PortalBlock | Teleporta para posição aleatória do mapa | ~1% dos tiles (base) |
| ShrinkBlock | Cubo fica metade, passo de 0.5 tile — permanente | ~2% dos tiles (base) |

**Fontes de alívio:**

| Fonte | Como funciona |
|---|---|
| HealBlock | +1 vida (máx. 3) |
| GrowBlock | Restaura tamanho normal após Shrink |
| CheckpointBlock | Salva ponto de respawn |

### 1.2 O que está ausente

- **Sem obstáculos físicos** no grid: todos os tiles são ou chão plano ou vazio. Não existe nada que bloqueie o movimento além das bordas do mapa.
- **Sem pressão de tempo**: o jogador pode parar, estudar o mapa, planejar. Não existe timer, ameaça que avança, ou deterioração do estado com o tempo.
- **Sem inimigos**: nenhuma entidade se move, persegue ou reage ao jogador.
- **Sem densidade de decisão**: na maioria dos tiles o jogador simplesmente rola em frente. Blocos especiais são pontuais e distribuídos sem contexto narrativo local.
- **Sem feedback de progressão dentro do nível**: não há contagem de distância percorrida, porcentagem de conclusão, ou indicação de proximidade do END.
- **Sem áudio**: ausência total de feedback sonoro elimina uma camada inteira de tension/release.
- **Mapa completamente visível**: a câmera orbital alta revela boa parte do labirinto. Não há neblina, bloqueio de visão ou incerteza espacial.

### 1.3 Consequência desses vazios

O jogo funciona como uma **demonstração técnica de CG** — o que é o objetivo acadêmico declarado. Mas como experiência de jogo, a progressão é previsível: o jogador olha o mapa, traça a rota até o END, executa, eventualmente cai e respawna, repete. Os blocos especiais são surpresas isoladas sem contexto, não escolhas ou desafios com peso.

---

## 2. Geração de Mapas — Análise de Game Design

Esta seção examina os parâmetros de geração procedural sob a ótica da experiência de jogo. O objetivo não é documentar o algoritmo (isso está em `RELATORIO_WORLD.md`), mas avaliar se os mapas gerados hoje produzem experiências interessantes.

### 2.1 Parâmetros atuais por dificuldade

Valores extraídos diretamente de `sandboxes/menu.py` — `_DIFFICULTIES`:

| Parâmetro | Fácil | Médio | Difícil |
|---|---|---|---|
| `cols × rows` | 24 × 14 = **336 tiles** | 36 × 20 = **720 tiles** | 56 × 30 = **1680 tiles** |
| `generator` | maze | maze | maze |
| `challenge_profile` | easy | medium | hard |
| `main_path_bias` | 0.78 | 0.62 | 0.52 |
| `branch_count` | 7 | 10 | 18 |
| `branch_length` | 7 | 11 | 18 |
| `dead_end_ratio` | 0.20 | 0.48 | 0.68 |
| `loop_regions` | 2 | 2 | 1 |
| `reward_branches` | 3 | 2 | 1 |
| `false_branches` | 2 | 5 | 10 |
| `false_branch_length` | 5 | 11 | 18 |
| `risk_shortcuts` | 1 | 1 | 1 |
| `safe_detours` | 2 | 0 | 0 |

**Probabilidades de poderes:**

| Power | Fácil | Médio | Difícil | Base (`Map`) |
|---|---|---|---|---|
| heal | 0.040 | 0.005 | 0.001 | 0.005 |
| shrink | 0.006 | 0.025 | 0.030 | 0.020 |
| grow | 0.006 | 0.002 | 0.002 | 0.015 |
| portal | 0.004 | 0.012 | 0.012 | 0.010 |
| ice | 0.012 | 0.018 | 0.028 | 0.030 |
| invert | 0.004 | 0.014 | 0.025 | 0.020 |
| fragile | 0.008 | 0.018 | 0.035 | 0.030 |
| bounce | 0.006 | 0.012 | 0.018 | 0.018 |
| slow | 0.008 | 0.010 | 0.014 | 0.015 |
| checkpoint | 0.020 | 0.012 | 0.008 | 0.012 |

---

### 2.2 Problemas identificados na geração atual

#### Problema G1 — Fácil é pequeno demais para ser interessante

Com 24 × 14 = 336 tiles e `main_path_bias = 0.78`, o caminho principal é quase reto. O walker raramente desvia muito antes de chegar ao END. Com `branch_length = 7` em um mapa de apenas 14 linhas, os ramos mal têm espaço para existir antes de bater na borda.

**Consequência:** O nível Fácil funciona como tutorial involuntário — o jogador vai do START ao END quase em linha reta. Não há exploração possível porque não há espaço para ela. A palavra "Fácil" resolve o problema por nomenclatura, mas a experiência não tem forma interessante.

**Indicador numérico do problema:**
```
branch_count = 7, branch_length = 7
Tiles potenciais de ramificação = 7 × 7 = 49
Tiles totais do mapa = 336
Cobertura máxima de ramos = ~14% do mapa
```
Com `dead_end_ratio = 0.20`, apenas ~2-3 ramos viram becos — não há dilema de exploração real.

---

#### Problema G2 — Difícil é grande demais para ser jogável com câmera fixa

Com 56 × 30 = 1680 tiles e câmera orbital a `camera_distance = 12`, o mapa extrapola o campo visual útil. O jogador não consegue ver o END nem estimar a direção correta. Isso não cria desafio interessante — cria desorientação passiva.

`main_path_bias = 0.52` em um mapa de 56 colunas significa que o caminho principal pode acumular desvios de dezenas de tiles antes de convergir para o END pelo fallback Manhattan. O caminho fica longo, mas sem ritmo ou estrutura reconhecível.

**Consequência:** A dificuldade do nível Difícil vem principalmente do tamanho e da confusão de orientação, não de desafios de habilidade ou decisão. O jogador fica perdido, não desafiado.

---

#### Problema G3 — `false_branches` não funcionam como armadilhas efetivas

O gerador tenta criar ramos falsos que "não reconectam" e evitam o caminho principal (`is_near_main_path`). Mas em mapas pequenos (Fácil) o mapa não tem espaço para isso funcionar. Em mapas grandes (Difícil), os 10 ramos falsos se diluem nos 1680 tiles e raramente ficam no campo visual do jogador ao mesmo tempo que a decisão precisa ser tomada.

O intent no final do ramo falso é `slow`, `ice`, ou `grow` — mas o jogador que chegou até lá já sofreu o custo de distância. O reward/punição no final do beco é irrelevante comparado ao tempo perdido.

---

#### Problema G4 — `loop_regions` cai de 2 para 1 no Difícil

Intuitivamente, o nível mais difícil deveria ter **mais** bifurcações e decisões reais, não menos. Mas o Difícil tem apenas 1 `loop_region` contra 2 do Fácil e Médio. Loop regions são as únicas estruturas que criam decisão estratégica genuína (dois caminhos com consequências diferentes). Reduzir isso no nível mais avançado é o inverso do esperado.

---

#### Problema G5 — Desequilíbrio entre shrink e grow

No nível Difícil: `prob_shrink = 0.030` e `prob_grow = 0.002`. O ShrinkBlock é 15× mais provável que o GrowBlock. Como Shrink é permanente (o cubo não volta ao tamanho normal sozinho), o jogador no Difícil vai encolher e permanecer encolhido por praticamente todo o nível sem conseguir reverter.

Isso não é desafio — é degradação permanente de estado sem possibilidade de recuperação. O efeito é percebido como bug mais do que como mecânica.

---

#### Problema G6 — `risk_shortcuts` está em 1 em todas as dificuldades

Um único atalho de risco em qualquer dificuldade mal é perceptível. Em mapas de 56 × 30, um atalho com 2-3 blocos perigosos é irrelevante estatisticamente. A escada de dificuldade deveria amplificar essa dimensão, não mantê-la constante.

---

#### Problema G7 — Density de poderes vs. tamanho do mapa não escala junto

No Fácil, `prob_heal = 0.040` em 336 tiles → esperado ~13 tiles de cura.  
No Difícil, `prob_heal = 0.001` em 1680 tiles → esperado ~1-2 tiles de cura.

O mapa Difícil tem 5× mais tiles mas ~13× menos cura. A densidade relativa de recompensa colapsa no Difícil, enquanto a densidade de perigo aumenta. A jornada mais longa tem menos recursos distribuídos ao longo do caminho — não por design intencional de escassez, mas por falta de compensação de escala.

---

### 2.3 O que o gerador maze produz bem

Antes de listar melhorias, vale registrar o que funciona:

- **Conectividade garantida** pelo fallback Manhattan — nunca há mapa sem solução.
- **Variedade visual** real entre seeds: dois mapas com mesmo DifficultyConfig têm formas completamente diferentes.
- **Becos intencionais** via `dead_end_ratio` com poder no final — a estrutura de punição/recompensa existe, mesmo que subaproveitada.
- **Intents** funcionam corretamente: blocos de risco ficam em atalhos de risco, blocos de segurança ficam nos safe_detours.
- A proteção da zona de entrada (`zone < 0.18` sem dangers) evita o pior cenário: morrer logo no início sem ter aprendido nada.

---

### 2.4 Propostas de ajuste — sem código novo

Todos os ajustes abaixo são apenas mudanças em `DifficultyConfig` dentro de `sandboxes/menu.py`.

#### Proposta P1 — Rebalancear o Fácil para ter forma, não só tamanho

**Problema resolvido:** G1 (mapa pequeno demais para ter estrutura).

```
cols=32, rows=18  (576 tiles — +71% de espaço)
main_path_bias=0.72  (menos direto, mais curvas)
branch_count=10, branch_length=8
dead_end_ratio=0.25
loop_regions=3  (mais decisões reais)
reward_branches=4  (becos com recompensa frequentes — ensina a mecânica de exploração)
false_branches=2  (poucos becos falsos — não é punição ainda)
```

**Intenção:** O Fácil deve ensinar a forma do jogo. Mapas com forma interessante (bifurcações, recompensas visíveis) são mais fáceis de navegar do que mapas pequenos e retos — porque o jogador entende o que o mapa quer dele.

---

#### Proposta P2 — Conter o Difícil e aumentar a intensidade local

**Problema resolvido:** G2 (grande demais), G4 (menos loops), G6 (shortcuts constantes).

```
cols=44, rows=26  (1144 tiles — ainda grande, mas navegável)
main_path_bias=0.55  (mantém tortuosidade)
loop_regions=4  (mais decisões, não menos)
risk_shortcuts=3  (escala com dificuldade)
safe_detours=0  (mantém)
```

**Intenção:** Dificuldade por intensidade de decisão, não por desorientação por tamanho.

---

#### Proposta P3 — Corrigir o desequilíbrio shrink/grow

**Problema resolvido:** G5.

```
# Difícil:
prob_shrink=0.018  (reduz de 0.030)
prob_grow=0.010    (aumenta de 0.002)

# Médio:
prob_grow=0.006    (aumenta de 0.002)
```

**Intenção:** Shrink deve ser desafio gerenciável, não estado terminal. A ratio shrink:grow deve ficar em no máximo 3:1.

---

#### Proposta P4 — Compensar densidade de cura com escala do mapa

**Problema resolvido:** G7.

Em vez de probabilidade fixa, a lógica ideal seria `prob_heal` inversamente proporcional ao tamanho. Como isso exigiria mudança de código, a alternativa nos configs:

```
# Difícil (mapa ~1144 tiles com proposta P2):
prob_heal=0.004  (aumenta de 0.001 — ainda escasso mas não invisível)
prob_checkpoint=0.012  (aumenta de 0.008 — checkpoints mais frequentes em mapas longos)
```

---

#### Configurações propostas completas

| Parâmetro | Fácil atual | **Fácil proposto** | Médio atual | **Médio proposto** | Difícil atual | **Difícil proposto** |
|---|---|---|---|---|---|---|
| `cols × rows` | 24×14 | **32×18** | 36×20 | 36×22 | 56×30 | **44×26** |
| `main_path_bias` | 0.78 | **0.72** | 0.62 | 0.62 | 0.52 | 0.55 |
| `branch_count` | 7 | **10** | 10 | 12 | 18 | 18 |
| `branch_length` | 7 | **8** | 11 | 11 | 18 | 16 |
| `dead_end_ratio` | 0.20 | **0.25** | 0.48 | 0.45 | 0.68 | 0.65 |
| `loop_regions` | 2 | **3** | 2 | 3 | 1 | **4** |
| `reward_branches` | 3 | **4** | 2 | 2 | 1 | 1 |
| `false_branches` | 2 | 2 | 5 | 5 | 10 | 10 |
| `risk_shortcuts` | 1 | 1 | 1 | **2** | 1 | **3** |
| `safe_detours` | 2 | **3** | 0 | **1** | 0 | 0 |
| `prob_heal` | 0.040 | 0.035 | 0.005 | 0.005 | 0.001 | **0.004** |
| `prob_shrink` | 0.006 | 0.006 | 0.025 | 0.020 | 0.030 | **0.018** |
| `prob_grow` | 0.006 | 0.006 | 0.002 | **0.006** | 0.002 | **0.010** |
| `prob_checkpoint` | 0.020 | 0.020 | 0.012 | 0.012 | 0.008 | **0.012** |
| (demais poderes) | sem mudança | sem mudança | sem mudança | sem mudança | sem mudança | sem mudança |

> Valores em **negrito** diferem do atual.

---

### 2.5 Limitações estruturais do gerador atual — o que parâmetros não resolvem

Alguns problemas não são de configuração, são de arquitetura do gerador. Registrados aqui para decisão futura sobre o que exigiria mudança de código:

**L1 — Sem controle de densidade local de poderes.**
O sistema distribui poderes por probabilidade uniforme sobre todos os tiles. Não existe mecanismo para dizer "essa zona específica deve ter concentração alta de IceBlock" ou "esse corredor não deve ter nenhum poder". A única granularidade é `zone` (distância do START), que é global. Consequência: sequências intencionais de blocos especiais (ex: corredor de gelo que leva a um bounce que exige precisão) não são possíveis com o gerador atual.

**L2 — Becos falsos não têm comprimento garantido proporcional ao mapa.**
`false_branch_length` é um valor absoluto. Um beco de comprimento 11 em um mapa 36×20 é longo; em um mapa 56×30 é médio. A percepção de "falso" não escala com o mapa.

**L3 — O caminho principal não tem forma reconhecível.**
O Drunkard Walk produz caminhos orgânicos sem ritmo visual. Não há conceito de "zona de descanso", "área de desafio" ou "corredor de aproximação ao END". O jogador não tem leitura estrutural do mapa — tudo parece igualmente aleatório.

**L4 — START e END têm posições previsíveis.**
START é sempre `(1, rows//2)` e END é sempre na coluna `cols-2`. O jogador experiente sabe que deve ir para a direita. O elemento de descoberta da direção correta não existe.

---

## 3. Análise dos Sistemas Existentes

### 2.1 O que os blocos especiais fazem bem

**IceBlock** é o mais interessante mecanicamente: obriga o jogador a antecipar onde vai parar antes de pisar. Isso cria leitura de mapa e decisão com custo. Se o destino do slide for o vazio, o jogador perde uma vida — punição justa com aviso visual.

**FragileBlock** tem potencial de criar tensão de curto prazo: o tile desaparece e o jogador não pode retornar pela mesma rota. Mas na prática, como o respawn é na posição mais recente, a perda de acesso ao tile tem baixo impacto.

**BounceBlock** e **PortalBlock** são os que mais quebram o controle do jogador. O portal é especialmente brutal porque deposita o cubo em posição completamente aleatória — incluindo void. Interessante como elemento de caos, mas desorientador sem contexto.

**InvertBlock** é o que mais exige reaprendizado ativo. Cinco segundos de WASD invertido forçam o jogador a reconverter os comandos mentalmente, o que é genuinamente desafiador com tempo de reação.

**ShrinkBlock** é o mais subutilizado: o efeito é permanente, mas não cria novos desafios além de andar em passos de 0.5. O passo menor poderia abrir brechas para tiles especiais, mas o mapa não é desenhado para tirar proveito disso.

### 3.2 Problemas estruturais de game feel

**Problema 1 — Ausência de ritmo:** O jogo tem velocidade constante. Roll de 0.25s, pausa, roll de 0.25s. Não há aceleração, nem momentos de urgência, nem desaceleração para respirar. A única variação é o SlowBlock (0.5s), que vai na direção errada — torna o jogo mais monótono quando deveria ser mais tenso.

**Problema 2 — Punição sem variação:** Toda queda resulta em -1 vida e respawn. Não existe punição gradual (perder progresso no mapa, ser empurrado para zona anterior), nem punição severa diferenciada (cair de certas zonas custa mais).

**Problema 3 — Recompensas sem escolha:** HealBlock e CheckpointBlock aparecem no caminho e são coletados passivamente. O jogador nunca precisa decidir *se* vale a pena desviar para pegar uma recompensa — ela simplesmente está no tile.

**Problema 4 — Mapa sem camadas de leitura:** O jogador vê todos os blocos especiais antes de chegar neles. Não há elemento de descoberta: a câmera alta torna tudo legível de longe.

---

## 4. Vetores de Melhoria — Análise

Esta seção organiza as direções possíveis de evolução. **Não são decisões tomadas** — são percepções organizadas para facilitar escolhas futuras.

### 4.1 Vetor A — Aplicar configurações propostas na seção 2

**O que é:** Usar melhor os parâmetros de geração procedural já existentes para criar mapas com mais identidade e tensão estrutural. As propostas P1–P4 da seção 2.4 cobrem os ajustes concretos. Sem código novo.

**Exemplos adicionais além das propostas P1–P4:**
- Combinar `false_branches` altos com `reward_branches` baixos para criar dilema "vale explorar?"
- Usar `risk_shortcuts` para criar atalhos perigosos com blocos de fragile/ice em sequência — risco vs. velocidade
- Ajustar as probabilidades base de IceBlock + FragileBlock em conjunto: uma zona com muitos tiles de gelo seguidos de bordas frágeis cria sequência de habilidade

**Custo:** Zero de desenvolvimento. Requer apenas ajuste de `DifficultyConfig` no `sandboxes/menu.py`.  
**Limitação:** Não resolve os problemas estruturais listados em 2.5 (L1–L4). É otimização do que já existe.

---

### 4.2 Vetor B — Pressão de tempo

**O que é:** Introduzir algum mecanismo que faça o tempo passar a ter peso na partida. O jogador que demora paga algum custo.

**Formas possíveis (sem ranking — apenas análise):**

**B1 — Timer de nível:** Contador regressivo visível. Se zerar, perde 1 vida e reseta. Simples de implementar, mas hostil para um jogo sem indicação clara de distância até o END.

**B2 — Tiles que deterioram:** Blocos do mapa têm uma vida útil. Cada vez que o jogador passa sobre um tile, ele fica marcado. Após N passagens, o tile vira void. Cria pressão de não repetir rotas — compatível com o FragileBlock existente, mas como sistema global.

**B3 — "Sombra" perseguidora:** Uma entidade sem corpo visível que avança pelo caminho mais curto até o jogador. Se alcançar, -1 vida. Não precisa de IA complexa — só BFS do end para o player. Cria urgência de movimento sem adicionar inimigos complexos.

**B4 — Zona de colapso:** O mapa tem uma borda que avança gradualmente da direção oposta ao END. Tiles fora da borda caem no void. Obriga o jogador a sempre avançar.

**Observação:** Qualquer mecanismo de pressão de tempo exige que o jogador consiga estimar sua distância até o END. Atualmente não existe indicador de progresso no HUD.

---

### 4.3 Vetor C — Obstáculos no grid

**O que é:** Tiles que não são pisáveis mas também não são void — são barreiras físicas que o jogador precisa contornar.

**Diferença do sistema atual:** Hoje, um tile inexistente no mapa é simplesmente ausência. Um obstáculo seria um tile presente, visível, mas intransponível.

**Formas possíveis:**

**C1 — WallBlock:** Bloco alto e opaco que bloqueia o movimento naquela direção. Já existe infraestrutura no `Block` para `active=False` (tile presente mas impassável). Um WallBlock seria um Block com `can_move_to = False` mas com renderização diferente.

**C2 — SpikesBlock:** Tile que mata instantaneamente ao pisar (0 vidas removidas, vai direto para -1 vida em vez de -1 vida). Diferente do void porque é visível e intencional.

**C3 — MovingBlock:** Um tile que alterna entre presente e ausente em ciclos de tempo. Cria ritmo de janela de oportunidade — uma mecânica clássica de plataforma adaptada para grade.

**Observação sobre C1:** A estrutura de `can_move_to` já suporta tiles impassáveis. Um WallBlock mudaria a leitura visual do mapa sem exigir mudanças na state machine do Cube.

---

### 4.4 Vetor D — Inimigos simples

**O que é:** Entidades que se movem no grid e causam consequência quando alcançam o jogador.

**Premissa importante:** O Cube tem uma state machine bem definida com validação de movimento via `MovementValidator`. Um inimigo simples NÃO precisa usar o mesmo sistema — pode ser uma entidade independente que só verifica se sua posição coincide com a do Cube.

**Formas possíveis (em ordem de complexidade de implementação):**

**D1 — Patrol enemy:** Se move em linha reta pelo grid, reverte ao bater na borda ou num tile vazio. Se o Cube está no mesmo tile, -1 vida. Sem IA, sem pathfinding. Implementável em ~50 linhas.

**D2 — Chaser (BFS):** Se move 1 tile por segundo em direção ao Cube usando BFS. Cria pressão de movimento real. Exige que o Cube também tenha representação de posição legível por entidades externas (já tem via `get_grid_position()`).

**D3 — Ghost:** Se move pelo mapa ignorando regras de tile (passa por void). Inatingível pelo jogador, apenas persegue. Cria pressão psicológica sem exigir que o jogador "mate" o inimigo.

**Observação sobre D:** Qualquer inimigo cria a necessidade de distinguir "onde o jogador está" de "onde o inimigo está" no mesmo frame. O `Map._grid` atual é só blocos — inimigos seriam uma nova camada de entidades sobre o mapa.

---

### 4.5 Vetor E — Enriquecer os poderes existentes

**O que é:** Tornar os poderes mais consequentes sem adicionar novos.

**ShrinkBlock está subutilizado.** O tamanho menor poderia:
- Permitir passar por aberturas de 0.5 tile que bloqueariam o cubo normal (requer mapas com tiles de passagem estreita)
- Permitir pisar em tiles marcados como "small-only" — tiles normais que se tornam transitáveis apenas no estado encolhido
- Aumentar o perigo de queda porque o step de 0.5 torna os movimentos de borda muito mais granulares

**CheckpointBlock está muito passivo.** O jogador pisa e esquece. Poderia:
- Ter limite de usos (2 respawns por checkpoint, depois some)
- Ser destruído pelo FragileBlock — criar tensão de "meu checkpoint vai sumir"
- Ser opcional e visível de longe, exigindo um desvio consciente

**PortalBlock é caótico demais.** A posição aleatória elimina toda agency. Alternativas:
- Portal com destino fixo visible (como uma linha entre os dois tiles)
- Portal unidirecional: A→B, mas B está em zona diferente do mapa
- Portal que o jogador pode evitar (tile adjacente ao portal fica marcado, cubo só é teletransportado se parar exatamente nele)

---

### 4.6 Vetor F — Feedback e legibilidade

**O que é:** Melhorar a comunicação do estado do jogo sem mudar as mecânicas.

**F1 — Indicador de progresso:** Barra ou número no HUD mostrando proximidade do END. Já existe `distance_from_start` calculado pelo BFS na geração — poderia ser exposto.

**F2 — Highlight do caminho até o END:** Ao pressionar uma tecla, mostrar brevemente o caminho mais curto calculado pelo BFS. Não quebra o desafio — o jogador já pode ver o mapa — mas reduz frustração de desorientação.

**F3 — Timer visual de poderes ativos:** InvertBlock tem 5s de duração, mas não existe indicador visual da contagem regressiva. O jogador não sabe quando os controles vão normalizar. Um ícone com timer no HUD resolveria isso.

**F4 — Fog of war parcial:** Revelar apenas os tiles a N células de distância do Cube. Cria incerteza espacial e torna a câmera alta menos vantajosa. Implementável desativando o `draw()` de blocos fora do raio.

---

## 5. Matriz de Impacto × Esforço

Avaliação para priorização. Escala: baixo / médio / alto.

| Melhoria | Impacto na Jogabilidade | Esforço de Impl. | Compatível com Arq. Atual |
|---|---|---|---|
| P1–P4 — Rebalancear DifficultyConfig (seção 2.4) | **Alto** | **Baixo** | Sim, só menu.py |
| F3 — Timer visual de poderes | Médio | Baixo | Sim, só HUD |
| F1 — Indicador de progresso | Médio | Baixo | Sim, BFS já existe |
| C1 — WallBlock | Médio | Baixo | Sim, Block já suporta |
| C3 — MovingBlock (tile pulsante) | Alto | Médio | Sim, usa `update()` |
| D1 — Patrol enemy | Alto | Médio | Sim, entidade independente |
| B3 — Sombra perseguidora | Alto | Médio | Sim, BFS já existe |
| E — ShrinkBlock com tiles small-only | Alto | Médio | Parcialmente |
| D2 — Chaser (BFS) | Alto | Médio-alto | Sim, com nova camada de entidades |
| B1 — Timer de nível | Médio | Baixo | Sim, só HUD + condição |
| B4 — Zona de colapso | Alto | Alto | Exige mudança no Map.update() |
| F4 — Fog of war | Médio | Médio | Sim, filtro no draw() |

---

## 6. Questões Abertas

Perguntas que precisam de decisão antes de qualquer implementação:

1. **O jogo deve permanecer um puzzle puro (sem pressão de tempo) ou virar um jogo de ação-puzzle?** Pressão de tempo muda fundamentalmente o tom — de contemplativo para reativo.

2. **Inimigos devem ser introduzidos?** Um inimigo simples de patrulha é tecnicamente trivial, mas muda a identidade do jogo. O projeto é demonstração de CG ou pretende ser um jogo completo?

3. **O ShrinkBlock deve ganhar utilidade tática (tiles small-only)?** Isso exige mudanças no gerador de mapas e no Block para suportar o conceito de "passagem estreita".

4. **O PortalBlock deve ser reformulado ou removido?** Na forma atual ele é mais punição aleatória do que mecânica de habilidade. Reformular exige decisão sobre para onde o portal deve levar.

5. **Deve existir um sistema de score/pontuação?** Atualmente não há recompensa por explorar ou por completar rápido. Um score baseado em tempo + vidas restantes + tiles explorados criaria objetivo secundário.

---

## 7. Registro de Decisões

*Seção para documentar decisões tomadas conforme o desenvolvimento avança.*

| Data | Decisão | Motivação |
|---|---|---|
| — | — | — |

---

*Documento iniciado em 2026-05-23. Atualizar conforme decisões forem tomadas.*
