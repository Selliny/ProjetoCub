# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 11. Mecânicas do Jogo — Resumo

### 11.1 Movimento

- Cubo rola 1 célula de grid por keypress (WASD).
- Roll normal: `0.25s`; com SlowBlock ativo: `0.5s`.
- Permite enfileirar 1 comando durante o roll.
- Controles podem estar invertidos (InvertBlock): W↔S, A↔D.

### 11.2 Poderes (10 tipos)

| # | Power | Duração | Consumido? | Efeito |
|---|---|---|---|---|
| 1 | Heal | Imediato | Sim | +1 vida (até max 3) |
| 2 | Shrink | Permanente | Não | Cubo ½ tamanho, step 0.5 |
| 3 | Grow | Imediato | Sim | Restaura tamanho normal |
| 4 | Portal | Imediato | Sim | Teleporta com fade; pode cair |
| 5 | Ice | 3 passos | Não | Auto-slide na direção do roll |
| 6 | Invert | 5s | Sim | Inverte WASD; toggle |
| 7 | Fragile | 1.5s após sair | Não | Bloco desaparece |
| 8 | Bounce | Imediato | Não | Pula 2 células (ou 1) |
| 9 | Slow | 3 movimentos | Sim | Roll 2× mais lento |
| 10 | Checkpoint | Permanente | Não | Salva respawn |

### 11.3 Sistema de Vidas e Respawn

- 3 vidas iniciais.
- Queda (tile vazio): -1 vida → animação de queda (0.5s) → fade in (0.4s) → respawn.
- Respawn: checkpoint ativo (se houver) ou último tile walkable visitado.
- `is_dead` quando `lives == 0`: game over, tela de fim exibida.

### 11.4 Condição de Vitória

- Cubo alcança o `EndBlock` → `reached_end = True`.
- Game loop detecta `reached_end && state == IDLE` → mostra tela de conclusão → próxima dificuldade.

---

## 12. Padrões de Design

| Padrão | Onde | Motivação |
|---|---|---|
| **Composição** | `Cube` e `Block` compõem `Color`, `Position`, `Size` | Reutilização sem herança desnecessária |
| **State Machine** | `CubeState` enum + `update()` | Controle explícito de animações e transições |
| **Protocol (Duck Typing)** | `MovementValidator` | `Map` implementa a interface sem herança formal |
| **Lazy Caching** | `TextureManager._cache` | Evita carregamento duplicado de texturas |
| **Command Queue** | `_queued` no `Cube` | Permite buffering de 1 input durante roll |
| **Observer (parcial)** | `schedule_fragile`, `set_checkpoint` | `Map` notificado pelo `Cube` via validator |
| **Template Method** | `Block._draw_top_textured()` sobrecarregado | Subclasses personalizam renderização do topo |
| **Factory Method** | `_make_powered(power_name, pos)` | Instancia subclasse correta por nome |

---

## 13. Estado Atual e Limitações

### 13.1 Funcionalidades Implementadas

- Jogo completo: menu → 3 dificuldades → tela de fim
- 10 tipos de poderes com comportamentos distintos
- 2 algoritmos de geração procedural (Loop Central + Drunkard Walk)
- Sistema de checkpoint e vidas
- HUD com corações e legenda de poderes
- Câmera orbital com suavização
- Controles invertidos temporários
- Sandboxes de teste isolados
- Texturas OpenGL com cache e recarga automática

### 13.2 Limitações e Ausências

| Item | Observação |
|---|---|
| Áudio | Nenhuma implementação de som ou música |
| Partículas/VFX | Apenas alpha blending; sem partículas |
| Save/Load | Nenhum sistema de persistência entre sessões |
| `Camera` class | Definida mas não usada pelo `main.py` (câmera orbital própria) |
| `Scene` class | Definida mas não usada pelo `main.py` |
| `InputHandler` | Definido mas supersedido por polling direto |
| OpenGL moderno | Usa immediate mode (glBegin/glEnd); sem VAO/VBO/GLSL |
| Testes unitários | Sem framework; testes manuais via sandboxes |
| Multiplayer | Não implementado |
| Mobile/touch | Não implementado |
| Fullscreen real | Modo janela configurável, não modo exclusivo |

---

## 14. Tabela de Arquivos

| Arquivo | Linhas | Papel |
|---|---|---|
| `main.py` | 467 | Game loop, câmera, HUD, orquestração |
| `src/entities/cube.py` | 704 | Cubo jogável (state machine, física, poderes) |
| `src/entities/block.py` | 589 | Hierarquia de blocos (10 poderes) |
| `src/world/map.py` | 977 | Geração procedural + validação de movimento |
| `src/graphics/color.py` | ~15 | Encapsulamento RGBA |
| `src/graphics/position.py` | ~19 | Vetor 3D |
| `src/graphics/size.py` | ~18 | Fatores de escala |
| `src/graphics/camera.py` | 111 | Câmera livre (yaw/pitch/zoom) |
| `src/graphics/texture.py` | ~81 | Gerenciador de texturas OpenGL |
| `src/world/scene.py` | ~20 | Agregador Cube + Map |
| `src/input/handler.py` | ~27 | Dispatcher de teclado |
| `sandboxes/sandbox_cube.py` | 429 | Sandbox de integração |
| `sandboxes/sandbox_block.py` | 185 | Sandbox de bloco único |
| `sandboxes/sandbox_map.py` | 345 | Editor de grid |
| `sandboxes/sandbox_scene.py` | ~28 | Sandbox de cena |
| `sandboxes/_harness.py` | 99 | Framework OpenGL compartilhado |
| `sandboxes/menu.py` | 468 | Menu + telas de dificuldade/fim |
| **Total** | **~4.582** | |

---

*Relatório gerado automaticamente em 2026-05-22 com base no estado da branch `main` (commit `473903c`).*
