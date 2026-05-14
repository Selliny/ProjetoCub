import pygame
from config import TAMANHO_BLOCO, COR_CAMINHO, COR_VAZIO, COR_COMECO, COR_FINAL, COR_LINHA

# Matriz 16x16
# Substituí o início (linha 0, coluna 10) por '2' 
# e o final (linha 15, colunas 7 e 8) por '3'
MATRIZ_MAPA = [
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0 , 2 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0 , 1 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0 , 1 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1 , 1 , 1, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1 , 1 , 1, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1 , 1 , 1, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 0, 0 , 0 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1 , 1 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 1, 1, 1, 1 , 1 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1 , 1 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1 , 1 , 1, 1 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 1 , 1 , 1, 1 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 1 , 1 , 1, 1 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0 , 0 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1, 1, 0 , 0 , 0, 0 ,0 ,0, 0],
    [0, 0, 0, 0, 0, 0, 0, 3, 3, 0 , 0 , 0, 0 ,0 ,0, 0]
]

def gerar_superficie_mapa():
    """Desenha a matriz em uma superfície Pygame e a retorna."""
    largura = len(MATRIZ_MAPA[0]) * TAMANHO_BLOCO
    altura = len(MATRIZ_MAPA) * TAMANHO_BLOCO
    superficie = pygame.Surface((largura, altura))

    for linha in range(len(MATRIZ_MAPA)):
        for coluna in range(len(MATRIZ_MAPA[linha])):
            valor_bloco = MATRIZ_MAPA[linha][coluna]
            
            # Verifica o valor e atribui a cor correta
            if valor_bloco == 1:
                cor = COR_CAMINHO
            elif valor_bloco == 2:
                cor = COR_COMECO
            elif valor_bloco == 3:
                cor = COR_FINAL
            else:
                cor = COR_VAZIO
                
            x = coluna * TAMANHO_BLOCO
            y = linha * TAMANHO_BLOCO
            pygame.draw.rect(superficie, cor, (x, y, TAMANHO_BLOCO, TAMANHO_BLOCO))
            # Linhas da grade
            pygame.draw.rect(superficie, COR_LINHA, (x, y, TAMANHO_BLOCO, TAMANHO_BLOCO), 1)
            
    return superficie