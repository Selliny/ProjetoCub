# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 5. Módulo `src/entities/` — Block e Hierarquia

### 4.2 `Block` e Hierarquia — `src/entities/block.py` (589 linhas)

Representa as células do mapa. Desenhadas como blocos planos de altura `0.1` em escala de jogo.

#### 4.2.1 `Block` (classe base)

**Constantes:**

| Constante | Valor | Descrição |
|---|---|---|
| `HEIGHT` | `0.1` | Altura padrão do bloco |
| `TEXTURE_PATH` | `"assets/textures/grass.png"` | Textura padrão |
| `_tex_id` | `None` | Cache de ID OpenGL por classe |

**Atributos de Instância:**

| Atributo | Tipo | Descrição |
|---|---|---|
| `position` | `Position` | Centro do bloco no mundo |
| `color` | `Color` | Cor base |
| `size` | `Size` | Escala (padrão `1.0 × 0.1 × 1.0`) |
| `active` | `bool` | Se False: não é desenhado e não é walkable |
| `is_powered` | `bool` | True apenas em subclasses de `PoweredBlock` |
| `textured` | `bool` | Se True: topo com textura; senão: cor sólida |

**Métodos:**

| Método | Assinatura | Descrição |
|---|---|---|
| `_get_tex` | `classmethod() → int` | Carrega/retorna ID OpenGL da textura |
| `reset_texture_cache` | `classmethod() → None` | Limpa `_tex_id` de toda a hierarquia |
| `_draw_top_textured` | `() → None` | Topo com textura `GL_QUADS` |
| `_draw_top_solid` | `(r, g, b) → None` | Topo sólido colorido |
| `_draw_sides` | `(r, g, b) → None` | 4 faces laterais com intensidade reduzida |
| `draw` | `() → None` | `glPushMatrix → translate → scale → top → sides → glPopMatrix` |

**Rendering das Laterais** (multiplicadores de brilho por face):
- Frente/Trás: `0.7×`
- Direita/Esquerda: `0.6×`
- Base (inferior): `0.5×`

#### 4.2.2 Hierarquia Completa

```
Block
├── StartBlock
├── EndBlock
└── PoweredBlock
    ├── HealBlock
    ├── ShrinkBlock
    ├── GrowBlock
    ├── PortalBlock
    ├── IceBlock
    ├── InvertBlock
    ├── FragileBlock
    ├── BouncePadBlock
    ├── SlowBlock
    └── CheckpointBlock
```

#### 4.2.3 Subclasses e Suas Características

| Classe | Cor | Textura | Power | Visual Extra |
|---|---|---|---|---|
| `StartBlock` | Verde escuro (0.1, 0.45, 0.1) | Nenhuma | — | Cor sólida |
| `EndBlock` | Vermelho (0.78, 0.20, 0.20) | lava.jpg | — | Textura de lava |
| `HealBlock` | Rosa (1.0, 0.4, 0.7) | heart.png | heal | Overlay coração com blend |
| `ShrinkBlock` | Roxo (0.5, 0.0, 1.0) | shrink.png | shrink | Textura de redução |
| `GrowBlock` | Verde claro (0.2, 1.0, 0.2) | expand.webp | grow | Overlay expansão com blend |
| `PortalBlock` | Azul escuro (0.0, 0.1, 0.4) | portal.png | portal | Overlay portal com blend |
| `IceBlock` | Ciano (0.55, 0.88, 1.0) | Nenhuma | ice | Cruz branca desenhada via GL |
| `InvertBlock` | Magenta (0.85, 0.0, 0.55) | Nenhuma | invert | Duas setas opostas (triângulos) |
| `FragileBlock` | Cinza (0.72, 0.72, 0.72) | Nenhuma | fragile | Linhas de trinca (GL_LINE_LOOP) |
| `BouncePadBlock` | Laranja (1.0, 0.45, 0.0) | Nenhuma | bounce | Triângulo apuntando p/ cima |
| `SlowBlock` | Verde musgo (0.2, 0.45, 0.15) | Nenhuma | slow | Círculo + ponteiro de relógio |
| `CheckpointBlock` | Dourado (0.85, 0.65, 0.05) | Nenhuma | checkpoint | Bandeirinha; muda cor quando ativo |

**`CheckpointBlock`** tem atributo adicional:

| Atributo | Tipo | Descrição |
|---|---|---|
| `is_active_checkpoint` | `bool` | Altera visual quando True (topo amarelo brilhante, bandeira verde) |

**`FragileBlock`** tem atributos adicionais (para controle de timer futuro):

| Atributo | Tipo | Descrição |
|---|---|---|
| `_deactivate_at` | `float \| None` | Timestamp absoluto de desativação |
| `_blink_t` | `float` | Acumulador para efeito de piscar |

---
