"""Entidade jogável principal: o cubo controlado pelo teclado.

Compõe Color, Size e Position. Implementa tombamento (roll) sobre a aresta
inferior em 4 direções (±Z via ↑/↓, ±X via ←/→) — um toque = 90° animados.
"""

from OpenGL.GL import (
    GL_QUADS,
    glBegin,
    glColor3f,
    glEnd,
    glRotatef,
    glScalef,
    glTranslatef,
    glVertex3f,
)

from src.graphics.color import Color
from src.graphics.position import Position
from src.graphics.size import Size

# Graus avançados por chamada de update() — controla velocidade do roll.
_ROLL_STEP: float = 5.0


class Cube:
    def __init__(
        self,
        position: Position | None = None,
        color: Color | None = None,
        size: Size | None = None,
    ) -> None:
        # Centro do cubo. y=0.5 coloca a base no plano y=0.
        self.position = position if position is not None else Position(0.0, 0.5, 0.0)
        self.color = color if color is not None else Color(1.0, 0.0, 0.0)
        self.size = size if size is not None else Size.uniform(1.0)

        # Rotação acumulada permanente, separada por eixo.
        # Roll ±Z gira em torno do eixo X; roll ±X gira em torno do eixo Z.
        self._total_angle_z: float = 0.0  # acumula rolls frente/trás (±Z)
        self._total_angle_x: float = 0.0  # acumula rolls laterais (±X)

        # Estado do roll em andamento.
        self._rolling: bool = False
        self._roll_dir: int = 0        # +1 ou -1
        self._roll_axis: str = 'z'     # 'z' = frente/trás, 'x' = lateral
        self._roll_accum: float = 0.0  # graus já rotacionados neste passo (0→90)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------

    def start_roll(self, direction: int, axis: str = 'z') -> None:
        """Inicia um passo de tombamento de 90°.

        direction: +1 ou -1.
        axis: 'z' para frente/trás (↑/↓), 'x' para lateral (←/→).
        Ignorado se um roll já estiver em andamento.
        """
        if self._rolling:
            return
        self._rolling = True
        self._roll_dir = direction
        self._roll_axis = axis
        self._roll_accum = 0.0

    def update(self) -> None:
        """Avança a animação de roll. Chamar uma vez por frame."""
        if not self._rolling:
            return
        self._roll_accum += _ROLL_STEP
        if self._roll_accum >= 90.0:
            self._finalize_roll()

    def is_rolling(self) -> bool:
        return self._rolling

    def apply_transform(self) -> None:
        """Empurra as matrizes OpenGL do frame atual (posição + rotação de pivô).

        Deve ser chamado após glLoadIdentity() e antes de draw().
        """
        cx, cy, cz = self.position.x, self.position.y, self.position.z

        if not self._rolling:
            glTranslatef(cx, cy, cz)
            # Aplica rotações acumuladas de todos os rolls anteriores.
            glRotatef(self._total_angle_z, 1.0, 0.0, 0.0)
            glRotatef(self._total_angle_x, 0.0, 0.0, 1.0)
            glScalef(self.size.sx, self.size.sy, self.size.sz)
            return

        if self._roll_axis == 'z':
            self._apply_roll_z(cx, cy, cz)
        else:
            self._apply_roll_x(cx, cy, cz)

    def draw(self) -> None:
        """Desenha o cubo unitário centrado na origem com 6 faces coloridas."""
        glBegin(GL_QUADS)

        # Frente (+Z)  — vermelho
        glColor3f(1.0, 0.0, 0.0)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Trás (−Z)  — verde
        glColor3f(0.0, 1.0, 0.0)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)

        # Cima (+Y)  — azul
        glColor3f(0.0, 0.0, 1.0)
        glVertex3f(-0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)

        # Baixo (−Y)  — amarelo
        glColor3f(1.0, 1.0, 0.0)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, -0.5)

        # Direita (+X)  — laranja
        glColor3f(1.0, 0.5, 0.0)
        glVertex3f( 0.5, -0.5,  0.5)
        glVertex3f( 0.5, -0.5, -0.5)
        glVertex3f( 0.5,  0.5, -0.5)
        glVertex3f( 0.5,  0.5,  0.5)

        # Esquerda (−X)  — roxo
        glColor3f(0.5, 0.0, 1.0)
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5,  0.5)
        glVertex3f(-0.5,  0.5,  0.5)
        glVertex3f(-0.5,  0.5, -0.5)

        glEnd()

    # ------------------------------------------------------------------
    # Métodos internos
    # ------------------------------------------------------------------

    def _apply_roll_z(self, cx: float, cy: float, cz: float) -> None:
        """T·R·T⁻¹ para tombamento ±Z (frente/trás). Pivô na aresta inferior ±Z."""
        pz = 0.5 * self._roll_dir   # +0.5 (frente) ou -0.5 (trás)
        py = -0.5
        partial = self._roll_accum * self._roll_dir

        glTranslatef(cx, cy, cz)
        glTranslatef(0.0, py, pz)
        glRotatef(partial, 1.0, 0.0, 0.0)
        glTranslatef(0.0, -py, -pz)
        # Aplica rotação acumulada de rolls anteriores sobre o estado parcial.
        glRotatef(self._total_angle_z, 1.0, 0.0, 0.0)
        glRotatef(self._total_angle_x, 0.0, 0.0, 1.0)
        glScalef(self.size.sx, self.size.sy, self.size.sz)

    def _apply_roll_x(self, cx: float, cy: float, cz: float) -> None:
        """T·R·T⁻¹ para tombamento ±X (lateral). Pivô na aresta inferior ±X."""
        px = 0.5 * self._roll_dir   # +0.5 (direita) ou -0.5 (esquerda)
        py = -0.5
        # Roll para direita (+X, dir=+1): rotação negativa em Z (cubo cai para direita).
        partial = self._roll_accum * -self._roll_dir

        glTranslatef(cx, cy, cz)
        glTranslatef(px, py, 0.0)
        glRotatef(partial, 0.0, 0.0, 1.0)
        glTranslatef(-px, -py, 0.0)
        glRotatef(self._total_angle_z, 1.0, 0.0, 0.0)
        glRotatef(self._total_angle_x, 0.0, 0.0, 1.0)
        glScalef(self.size.sx, self.size.sy, self.size.sz)

    def _finalize_roll(self) -> None:
        """Conclui o roll: atualiza posição, acumula ângulo, reseta estado."""
        if self._roll_axis == 'z':
            self.position.z += 1.0 * self._roll_dir
            self._total_angle_z += 90.0 * self._roll_dir
        else:
            self.position.x += 1.0 * self._roll_dir
            self._total_angle_x += 90.0 * -self._roll_dir

        self._rolling = False
        self._roll_accum = 0.0
        self._roll_dir = 0

    # Mantidos para compatibilidade com InputHandler futuro
    def move(self, dx: float, dy: float, dz: float) -> None:
        self.position.translate(dx, dy, dz)

    def scale(self, factor: float) -> None:
        self.size.sx *= factor
        self.size.sy *= factor
        self.size.sz *= factor
