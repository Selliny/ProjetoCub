# ProjetoCub

Jogo educacional de um cubo 3D em **PyOpenGL** + **pygame** para estudo e aplicação de conceitos de **Computação Gráfica**. Um cubo é renderizado em uma cena 3D e movido pelo teclado, exercitando transformações geométricas (translação, rotação, escala) e o pipeline de renderização clássico do OpenGL.

## Objetivo acadêmico

Aplicar, na prática, os conceitos vistos em sala:

- Pipeline de renderização do OpenGL (modo imediato).
- Projeção perspectiva (`gluPerspective`).
- Matriz `MODELVIEW` e a sequência `glTranslatef → glRotatef → glScalef`.
- Teste de profundidade (`GL_DEPTH_TEST`).
- Transformações afins aplicadas a um objeto 3D em tempo real.

## Tecnologias

- **Python 3.11+**
- **PyOpenGL** — bindings Python para OpenGL.
- **pygame** — janela, loop principal e eventos de teclado.
- **numpy** — manipulação de vértices e matrizes.

Versões fixadas em [requirements.txt](requirements.txt).

## Arquitetura — Programação Orientada a Objetos

> **Importante:** este projeto é desenvolvido em **POO**. O esqueleto procedural fornecido pelo professor (mais abaixo) define o **fluxo do loop principal** que `main.py` deve seguir, mas **estado e comportamento** (posição, cor, escala, blocos do mapa, ações especiais) são modelados como **classes** que refletem conceitos do jogo e da computação gráfica — não como variáveis globais.

### Princípio de modelagem

Cada classe deve representar um **conceito reutilizável** do jogo ou da CG. A regra geral:

> *Se um atributo faz sentido para mais de um tipo de objeto da cena, ele vira sua própria classe.*

Conceitos puros de Computação Gráfica viram classes em [src/graphics/](src/graphics/), reutilizáveis por qualquer entidade desenhável. Entidades do jogo viram classes em [src/entities/](src/entities/), compostas a partir desses conceitos.

Exemplos atuais (a lista **não é fechada** — novas classes serão adicionadas conforme o jogo evolui, ex.: `Camera`, `Light`, `Material`, `Drawable`, `Player`):

| Classe | Pacote | Responsabilidade |
|---|---|---|
| `Color` | `graphics` | Encapsula RGBA. Centraliza `glColor4f` para qualquer objeto da cena. |
| `Size` | `graphics` | Fator de escala por eixo. Centraliza `glScalef`. |
| `Position` | `graphics` | Vetor `(x, y, z)`. Centraliza `glTranslatef`. |
| `Cube` | `entities` | Entidade jogável. *Tem-um* `Color`, *tem-um* `Size`, *tem-uma* `Position`, mais ângulo de rotação. |
| `Block` | `entities` | Bloco do mapa. Mesma composição do cubo + `active: bool` e `is_special: bool` (blocos especiais podem disparar ações). |
| `Map` | `world` | Coleção de `Block`s; sabe iterar e desenhar os blocos ativos. |
| `Scene` | `world` | Agrega `Cube` + `Map`. Expõe `draw()` chamado pelo loop principal. |
| `InputHandler` | `input` | Traduz eventos pygame em chamadas de método em `Cube`/`Scene`. |

### Diagrama de composição

```
Scene
├── Cube ── has-a ── Color, Size, Position, ângulo
└── Map
    └── Block[] ── has-a ── Color, Size, Position, active, is_special
```

A composição (`has-a`) é favorecida sobre herança nesta fase. `Block` pode futuramente herdar de uma superclasse comum (`Drawable`) junto com `Cube`, conforme o jogo cresce.

## Estrutura do projeto

```
ProjetoCub/
├── README.md                    Este arquivo.
├── requirements.txt             Dependências pinadas.
├── main.py                      Orquestrador — segue o padrão do professor.
└── src/
    ├── graphics/                Conceitos puros de CG (reutilizáveis).
    │   ├── color.py             Classe Color.
    │   ├── size.py              Classe Size.
    │   └── position.py          Classe Position.
    ├── entities/                Entidades do jogo.
    │   ├── cube.py              Classe Cube.
    │   └── block.py             Classe Block.
    ├── world/                   Agregação de entidades.
    │   ├── map.py               Classe Map.
    │   └── scene.py             Classe Scene.
    └── input/                   Entrada do usuário.
        └── handler.py           Classe InputHandler.
sandboxes/                       Sandboxes para desenvolvimento paralelo
├── _harness.py                  Plumbing OpenGL compartilhada.
├── sandbox_cube.py              Testa só o Cube.
├── sandbox_block.py             Testa só o Block.
├── sandbox_map.py               Testa só o Map.
└── sandbox_scene.py             Testa a Scene completa.
```

A separação entre `graphics/` e `entities/` é deliberada: conceitos de CG são reutilizáveis e independentes do jogo; entidades são específicas do domínio. A pasta `sandboxes/` é separada de `src/` porque contém arquivos **executáveis de desenvolvimento**, não código de produção (ver [sandboxes/README.md](sandboxes/README.md)).

## Como rodar

### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

A janela de 800×600 abrirá com fundo azul claro. Feche-a normalmente (X) para encerrar o loop.

## Desenvolvimento paralelo (sandboxes)

Cada integrante do grupo pode desenvolver e visualizar **sua parte isoladamente**, mesmo que as outras peças ainda não estejam prontas. Para isso existem os arquivos em [sandboxes/](sandboxes/) — um por componente, cada um abrindo sua própria janela OpenGL:

```powershell
python -m sandboxes.sandbox_cube     # só o cubo (com teclado)
python -m sandboxes.sandbox_block    # só um bloco
python -m sandboxes.sandbox_map      # só o mapa
python -m sandboxes.sandbox_scene    # cena completa (sem teclado)
```

Detalhes, regras de colaboração e divisão sugerida do grupo em [sandboxes/README.md](sandboxes/README.md).

## Controles do teclado

| Tecla | Ação |
|---|---|
| ← / → | Translação no eixo X |
| ↑ / ↓ | Translação no eixo Y (ou Z, conforme o jogo) |
| R | Rotação do cubo |
| + / − | Escala (a definir) |

Implementados em [src/input/handler.py](src/input/handler.py).

## Padrão de código (esqueleto do professor)

O bloco abaixo é o **template oficial fornecido pelo professor**. Ele define a **ordem das chamadas OpenGL** que `main.py` deve seguir. Em nossa implementação POO, este fluxo aparece quase idêntico em [main.py](main.py), mas:

- As **variáveis globais** (`pos_x`, `pos_y`, `pos_z`, `angulo_rotacao`, `escala_obj`) viram **atributos de objetos** (`Cube.position`, `Cube.angle`, `Cube.size`).
- Os `if event.key == ...` viram despacho de método em [src/input/handler.py](src/input/handler.py).
- A função `desenhar_cena()` vira o método `Scene.draw()`.
- A sequência `glTranslatef → glRotatef → glScalef` permanece, agora aplicada **dentro** de `Scene.draw()` lendo o estado dos objetos.

```python
import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *

# Variáveis globais
pos_x, pos_y, pos_z = 0, 0, -10
angulo_rotacao = 0
escala_obj = 1.0

def desenhar_cena():
    # Desativa o Culling para garantir que a face apareça de qualquer lado
    glDisable(GL_CULL_FACE)

def main():
    global pos_x, pos_y, pos_z, angulo_rotacao, escala_obj

    pygame.init()
    display = (800, 600)
    pygame.display.set_mode(display, DOUBLEBUF | OPENGL)

    # Configuração básica de renderização
    glViewport(0, 0, 800, 600)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45, (800/600), 0.1, 100.0)

    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    glEnable(GL_DEPTH_TEST)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()

            if event.type == KEYDOWN:
                if event.key == K_LEFT:
                if event.key == K_RIGHT:
                if event.key == K_UP:
                if event.key == K_DOWN:
                if event.key == K_r:

        # Limpa com azul claro
        glClearColor(0.2, 0.5, 0.8, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        glLoadIdentity()

        # Posicionamento
        glTranslatef(pos_x, pos_y, pos_z)
        glRotatef(angulo_rotacao, 0, 1, 0)
        glScalef(escala_obj, escala_obj, escala_obj)

        desenhar_cena()

        pygame.display.flip()
        pygame.time.wait(10)

if __name__ == "__main__":
    main()
```

## Conceitos de Computação Gráfica abordados

- Pipeline fixo do OpenGL (modo imediato com `glBegin` / `glEnd`).
- Projeção perspectiva via `gluPerspective(fov, aspect, near, far)`.
- Matriz `MODELVIEW` e a pilha de transformações.
- Teste de profundidade (`glEnable(GL_DEPTH_TEST)`).
- Transformações afins: translação (`glTranslatef`), rotação (`glRotatef`), escala (`glScalef`).
- Buffer duplo (`DOUBLEBUF`) e `pygame.display.flip()` para evitar tearing.

## Convenções de código

- **Módulos / funções**: `snake_case` (ex.: `add_block`, `is_special`).
- **Classes**: `PascalCase` em **inglês**, alinhando com a terminologia de CG (`Color`, `Position`, `Scene`).
- **Docstrings e comentários**: em **português**.
- **Uma classe por arquivo** (regra geral, não rígida).
- **Composição preferida sobre herança** nesta fase.

## Autoria

Trabalho da disciplina de **Computação Gráfica**. Aluno: _(preencher)_.
