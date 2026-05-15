"""Bloco do mapa e subclasse PoweredBlock.

Hierarquia:
    Block           — bloco comum, só forma o terreno, sem efeito de jogo.
    PoweredBlock    — herda Block e adiciona `power`, um identificador de
                      efeito que Scene aplica ao Cube quando ele pousa neste bloco.

Diferença entre Block e PoweredBlock
-------------------------------------
    Block:
        - is_powered = False  (padrão)
        - Não carrega nenhum efeito de jogo.
        - Representa caminho, chão, início ou fim — qualquer célula
          que o Cube pode cruzar sem consequência especial.

    PoweredBlock(power="scale"):
        - is_powered = True   (fixado pelo construtor via super())
        - Carrega o atributo `power` com o nome do efeito desejado.
        - Quando Scene detectar que o Cube pousou sobre esta célula,
          ela lê `block.power` e aplica o efeito correspondente ao Cube.
        - Efeitos planejados: "scale", "speed", "color" — mas qualquer
          string pode ser usada; Scene decide o que cada uma faz.

    Visualmente os dois são idênticos — a diferença é de dados, não de cor.
    Para distingui-los visualmente, basta passar uma `color` diferente
    ao construir o PoweredBlock (ex.: amarelo ouro).

Block inativo (active = False)
-------------------------------
    Qualquer Block (ou PoweredBlock) com `active=False` é ignorado
    completamente por `draw()` — como se não existisse no mapa.
    Usos típicos:
        - Traps ocultos: bloco existe no grid mas fica invisível até
          um evento de jogo ligar active=True.
        - Depuração: desligar um bloco específico sem removê-lo do Map.
    Para reativar: `block.active = True`

Como editar o poder de um PoweredBlock
----------------------------------------
    Poderes disponíveis (a Scene precisa reconhecer o valor):
        "scale"  → altera o tamanho do Cube
        "speed"  → altera a velocidade de rolamento do Cube
        "color"  → muda a cor do Cube

    Trocar o poder de um bloco já criado:
        block.power = "speed"           # direto no atributo

    Criar com poder específico:
        PoweredBlock(power="color", position=..., color=...)

    Adicionar um poder novo:
        1. Escolha um nome de string (ex.: "bounce").
        2. Crie o bloco: PoweredBlock(power="bounce", ...)
        3. Em Scene.draw() (ou método de colisão), adicione o caso:
               if block.power == "bounce":
                   cube.start_roll(...)   # lógica do efeito aqui
"""

from OpenGL.GL import (
    GL_QUADS,
    glBegin,
    glColor3f,
    glEnd,
    glPopMatrix,
    glPushMatrix,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size

# Altura padrão de um bloco (achatado no Y).
_BLOCK_HEIGHT: float = 0.1


class Block:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
        active: bool = True,
        is_powered: bool = False,
    ) -> None:
        # Onde o bloco está no espaço 3D. Padrão: origem (0, 0, 0).
        self.position = position if position is not None else Position()

        # Cor base do bloco. As faces laterais derivam dela com fator de escuro.
        self.color = color if color is not None else Color(0.5, 0.5, 0.5)

        # Escala nos 3 eixos. Y pequeno (0.1) dá o aspecto achatado de terreno.
        self.size = size if size is not None else Size(1.0, _BLOCK_HEIGHT, 1.0)

        # False = bloco invisível e sem colisão (draw() retorna imediatamente).
        self.active = active

        # True em PoweredBlock; usado por Scene para saber se deve ler .power.
        self.is_powered = is_powered

    def draw(self) -> None:
        # Bloco inativo: não renderiza nada — equivale a uma célula vazia visualmente.
        if not self.active:
            return
        r, g, b = self.color.r, self.color.g, self.color.b

        glPushMatrix()
        glTranslatef(self.position.x, self.position.y, self.position.z)
        glScalef(self.size.sx, self.size.sy, self.size.sz)

        glBegin(GL_QUADS)

        # Topo (+Y)
        glColor3f(r, g, b)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Base (−Y) — tom escuro
        glColor3f(r * 0.5, g * 0.5, b * 0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Frente (+Z) — tom médio
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Trás (−Z)
        glColor3f(r * 0.7, g * 0.7, b * 0.7)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Direita (+X)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (−X)
        glColor3f(r * 0.6, g * 0.6, b * 0.6)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()
        glPopMatrix()


class PoweredBlock(Block):
    # Herda tudo de Block — geometria, cor, posição, active.
    # A única adição é `power`: uma string que Scene lê para decidir o efeito.
    #
    # Por que herança e não um atributo em Block?
    #   Block não precisa saber de poderes — mantém a classe simples.
    #   PoweredBlock especializa apenas o que muda (is_powered=True + power).
    #   isinstance(block, PoweredBlock) é suficiente para Scene distinguir os dois.

    def __init__(self, power: str = "scale", **kwargs) -> None:
        # is_powered=True é passado para Block aqui — nunca precisa ser setado fora.
        super().__init__(is_powered=True, **kwargs)

        # Identificador do efeito que Scene vai aplicar ao Cube nesta célula.
        # Trocar em tempo real: block.power = "speed"
        self.power = power
