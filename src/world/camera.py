import pygame
from config import LARGURA_TELA, ALTURA_TELA

class Camera:
    def __init__(self):
        self.x = LARGURA_TELA // 2
        self.y = ALTURA_TELA // 2
        self.zoom = 1.0
        self.angulo_rotacao = 0
        self.inclinacao = 1.0
        self.vel_mov = 7

    def tratar_eventos_mouse(self, evento):
        """Lida com os eventos de scroll do mouse (Zoom)."""
        if evento.type == pygame.MOUSEWHEEL:
            if evento.y > 0:
                self.zoom += 0.1
            elif evento.y < 0:
                self.zoom -= 0.1
            self.zoom = max(0.3, min(self.zoom, 4.0))

    def atualizar_controles(self, teclas):
        """Lida com as teclas pressionadas para mover, girar e inclinar."""
        # Rotação (Q, E)
        if teclas[pygame.K_q]:
            self.angulo_rotacao += 3
        if teclas[pygame.K_e]:
            self.angulo_rotacao -= 3
            
        # Inclinação / Tilt (R, F)
        if teclas[pygame.K_r]:
            self.inclinacao += 0.02
        if teclas[pygame.K_f]:
            self.inclinacao -= 0.02
        self.inclinacao = max(0.2, min(self.inclinacao, 1.0))
            
        # Movimentação (WASD ou Setas)
        if teclas[pygame.K_w] or teclas[pygame.K_UP]:
            self.y += self.vel_mov
        if teclas[pygame.K_s] or teclas[pygame.K_DOWN]:
            self.y -= self.vel_mov
        if teclas[pygame.K_a] or teclas[pygame.K_LEFT]:
            self.x += self.vel_mov
        if teclas[pygame.K_d] or teclas[pygame.K_RIGHT]:
            self.x -= self.vel_mov

    def aplicar_transformacoes(self, superficie_original):
        """Aplica os cálculos de computação gráfica na imagem."""
        # 1. Rotação e Zoom
        mapa_transf = pygame.transform.rotozoom(superficie_original, self.angulo_rotacao, self.zoom)
        
        # 2. Inclinação (Achatamento no eixo Y)
        largura_atual = mapa_transf.get_width()
        altura_inclinada = int(mapa_transf.get_height() * self.inclinacao)
        
        if altura_inclinada > 0:
            mapa_final = pygame.transform.scale(mapa_transf, (largura_atual, altura_inclinada))
        else:
            mapa_final = mapa_transf
        
        # Centraliza a imagem na tela de acordo com a posição (x,y) da câmera
        rect_final = mapa_final.get_rect(center=(self.x, self.y))
        
        return mapa_final, rect_final