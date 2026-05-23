# Relatório Técnico — ProjetoCub

**Data de geração:** 2026-05-22  
**Versão da aplicação:** branch `main` (commit mais recente: `473903c`)

---

## 1. Visão Geral

**ProjetoCub** é um jogo 3D educacional desenvolvido com **PyOpenGL + pygame** em Python 3.11+, concebido para demonstrar conceitos práticos de computação gráfica: transformações de objetos (translação, rotação, escala), câmera livre em perspectiva, pipeline de renderização OpenGL, física de queda e sistemas de animação baseados em delta-time.

O jogo é um platformer/labirinto em perspectiva de terceira pessoa. O jogador controla um cubo que deve rolar de uma célula START até uma célula END, atravessando um mapa gerado proceduralmente. O mapa é composto de blocos que podem ter poderes distintos, alterando o comportamento do cubo ou do mapa.

### 1.1 Stack Tecnológico

| Biblioteca | Versão | Papel |
|---|---|---|
| Python | 3.11+ | Linguagem principal |
| pygame | 2.6.1 | Janela, input, superfícies 2D |
| PyOpenGL | 3.1.7 | Bindings OpenGL (immediate mode) |
| PyOpenGL-accelerate | 3.1.7 | Otimizações SIMD |
| numpy | 2.1.3 | Operações numéricas auxiliares |

---

## 2. Estrutura de Diretórios

```
ProjetoCub/
├── main.py                          # Ponto de entrada e game loop principal
├── requirements.txt                 # Dependências Python
├── README.md                        # Documentação do projeto
├── RELATORIO.md                     # Relatório técnico completo
│
├── assets/
│   └── textures/
│       ├── grass.png                # Topo dos blocos normais
│       ├── heart.png                # Overlay do HealBlock
│       ├── portal.png               # Overlay do PortalBlock
│       ├── shrink.png               # Overlay do ShrinkBlock
│       ├── expand.webp              # Overlay do GrowBlock
│       ├── lava.jpg                 # Topo do EndBlock
│       └── rock.jpg                 # Textura alternativa (não utilizada)
│
├── src/                             # Código de produção (organizado por POO)
│   ├── graphics/                    # Primitivas de computação gráfica reutilizáveis
│   │   ├── color.py                 # Encapsulamento RGBA
│   │   ├── position.py              # Vetor 3D (x, y, z)
│   │   ├── size.py                  # Fatores de escala (sx, sy, sz)
│   │   ├── camera.py                # Câmera livre com yaw/pitch/zoom
│   │   └── texture.py               # TextureManager com cache OpenGL
│   │
│   ├── entities/                    # Entidades do jogo
│   │   ├── cube.py                  # Cubo jogável — state machine + física
│   │   └── block.py                 # Bloco do mapa e 10 subclasses de poderes
│   │
│   ├── world/                       # Camada de agregação do mundo
│   │   ├── map.py                   # Geração procedural + validação de movimento
│   │   └── scene.py                 # Agregador Cube + Map
│   │
│   └── input/
│       └── handler.py               # Dispatcher de eventos de teclado
│
└── sandboxes/                       # Ambientes de teste isolados
    ├── _harness.py                  # Plumbing OpenGL compartilhado
    ├── sandbox_cube.py              # Teste: cubo + mapa + câmera
    ├── sandbox_block.py             # Teste: bloco único interativo
    ├── sandbox_map.py               # Teste: editor de grid
    ├── sandbox_scene.py             # Teste: agregação da cena
    ├── menu.py                      # Menu de dificuldade + tela de fim
    └── README.md                    # Guia de uso dos sandboxes
```

---
