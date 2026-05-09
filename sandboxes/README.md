# Sandboxes

Cada arquivo `sandbox_*.py` permite testar uma parte isolada do jogo enquanto outras ainda estão sendo implementadas. Útil para o trabalho **paralelo em grupo**: cada integrante desenvolve sua peça sem depender de o colega ter terminado a dele.

Todos os sandboxes compartilham [_harness.py](_harness.py), que cuida da plumbing OpenGL (janela, projeção perspectiva, depth test, loop de frames). O sandbox em si só precisa montar o objeto e dizer **o que desenhar a cada frame**.

## Como rodar

A partir da **raiz do projeto** (`ProjetoCub/`), com o venv ativado:

```powershell
python -m sandboxes.sandbox_cube
python -m sandboxes.sandbox_block
python -m sandboxes.sandbox_map
python -m sandboxes.sandbox_scene
```

> **Importante:** use `python -m sandboxes.sandbox_X` — **não** `python sandboxes/sandbox_X.py`. A flag `-m` faz o Python tratar a raiz do projeto como diretório de trabalho, o que é necessário para os imports `from src.entities.cube import Cube` resolverem corretamente.

Se nada for desenhado (janela 800×600 azul vazia), provavelmente o `draw()` da classe ainda está como `pass` — esse é o estado inicial. Quando o desenho for implementado, o objeto aparece automaticamente sem mexer no sandbox.

## Sandboxes disponíveis

| Sandbox | Arquivo de produção testado | Notas |
|---|---|---|
| [sandbox_cube.py](sandbox_cube.py) | [src/entities/cube.py](../src/entities/cube.py) | Cubo com `InputHandler` ligado (←/→/↑/↓/R) |
| [sandbox_block.py](sandbox_block.py) | [src/entities/block.py](../src/entities/block.py) | Bloco fixo no centro; **espaço** alterna `active` |
| [sandbox_map.py](sandbox_map.py) | [src/world/map.py](../src/world/map.py) | Grade 3×3 de blocos para validar iteração e layout |
| [sandbox_scene.py](sandbox_scene.py) | [src/world/scene.py](../src/world/scene.py) | Cena completa, sem teclado — espelha o `main.py` |

## Sugestão de divisão do grupo

| Integrante | Sandbox | Mexe em (produção) |
|---|---|---|
| _A_ | `sandbox_cube` | `src/entities/cube.py` + `src/input/handler.py` |
| _B_ | `sandbox_block` | `src/entities/block.py` |
| _C_ | `sandbox_map` | `src/world/map.py` |
| _D_ | `sandbox_scene` (integrador) | `src/world/scene.py` + `main.py` |

Conceitos puros de CG ([src/graphics/](../src/graphics/) — `Color`, `Size`, `Position`) são editados por quem precisar; mudanças ali afetam todo mundo, então combinem antes.

## Regras

- Cada integrante mexe **só** no seu arquivo de produção em `src/` + no seu `sandbox_*.py`.
- Sandboxes **não importam outros sandboxes**.
- Se você precisa de algo que o colega ainda não implementou, **não importe a versão pela metade** — desenhe um placeholder local dentro do seu sandbox e remova quando o colega terminar.
- O harness ([_harness.py](_harness.py)) é compartilhado: mude com cuidado e avise o grupo.

## Quando deletar esta pasta?

Opcional. Depois que o `main.py` integrador estiver maduro, a pasta pode permanecer como ferramenta de debug — útil sempre que um componente regredir e for preciso isolá-lo de novo.
