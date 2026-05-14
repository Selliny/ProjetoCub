import pygame
from config import LARGURA_TELA, ALTURA_TELA, COR_FUNDO, FPS
from mapa import gerar_superficie_mapa
from camera import Camera

def main():
    # Inicialização
    pygame.init()
    tela = pygame.display.set_mode((LARGURA_TELA, ALTURA_TELA))
    pygame.display.set_caption("Motor Gráfico - Mapa de Tabuleiro")
    relogio = pygame.time.Clock()

    # Instanciando nossos módulos
    superficie_mapa = gerar_superficie_mapa()
    camera = Camera()

    rodando = True

    while rodando:
        # 1. Captura de Eventos
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False
            
            # Passa eventos de mouse para a câmera
            camera.tratar_eventos_mouse(evento)

        # 2. Atualização de Lógica
        teclas = pygame.key.get_pressed()
        camera.atualizar_controles(teclas)

        # 3. Renderização na Tela
        tela.fill(COR_FUNDO)
        
        # A câmera pega o mapa base e devolve a versão processada em CG
        mapa_final, rect_final = camera.aplicar_transformacoes(superficie_mapa)
        
        tela.blit(mapa_final, rect_final.topleft)

        pygame.display.flip()
        relogio.tick(FPS)

    pygame.quit()

if __name__ == "__main__":
    main()