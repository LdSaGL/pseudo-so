"""
Modulo de Memoria.

Simula a memoria principal por paginacao com memoria virtual:
  - 20 frames de 1k no total;
  - 8 frames reservados para processos de tempo real (indices 0..7);
  - 12 frames para processos de usuario (indices 8..19);
  - as duas areas NUNCA se misturam (protecao entre as classes);
  - cada processo so enxerga os seus proprios frames (protecao entre processos);
  - substituicao de paginas por LRU (Least Recently Used) em escopo LOCAL;
  - pre-carga de 1 pagina (a primeira referencia nao conta como falta).
"""


class GerenciadorMemoria:
    """Gerencia a alocacao de frames e o calculo de faltas de pagina."""

    TOTAL_FRAMES = 20
    FRAMES_TEMPO_REAL = 8          # frames 0..7
    FRAMES_USUARIO = 12            # frames 8..19
    TAMANHO_FRAME_KB = 1

    def __init__(self):
        # Listas de frames livres em cada area reservada.
        self.livres_tempo_real = list(range(0, self.FRAMES_TEMPO_REAL))
        self.livres_usuario = list(
            range(self.FRAMES_TEMPO_REAL, self.TOTAL_FRAMES))

    def _pool(self, processo):
        """Devolve a lista de frames livres da area do processo."""
        if processo.eh_tempo_real:
            return self.livres_tempo_real
        return self.livres_usuario

    def _capacidade(self, processo):
        """Capacidade TOTAL (livre + ocupada) da area do processo."""
        if processo.eh_tempo_real:
            return self.FRAMES_TEMPO_REAL
        return self.FRAMES_USUARIO

    def cabe_na_area(self, processo):
        """
        Indica se o working set do processo cabe na capacidade TOTAL da sua
        area de memoria, ainda que no momento a area esteja ocupada.

        Diferente de 'tem_espaco', que verifica a disponibilidade atual, este
        metodo detecta processos impossiveis de admitir (working set maior que
        toda a area reservada), evitando reenfileiramento infinito.
        """
        return processo.tamanho_working_set <= self._capacidade(processo)

    def tem_espaco(self, processo):
        """Verifica se ha frames livres suficientes para o working set."""
        return len(self._pool(processo)) >= processo.tamanho_working_set

    def alocar(self, processo):
        """
        Aloca 'working_set' frames da area correta para o processo.
        Garante que tempo real e usuario nunca compartilham frames.
        """
        if not self.tem_espaco(processo):
            return False
        pool = self._pool(processo)
        for _ in range(processo.tamanho_working_set):
            processo.frames_alocados.append(pool.pop(0))
        return True

    def liberar(self, processo):
        """Devolve os frames do processo para a area de origem."""
        pool = self._pool(processo)
        pool.extend(processo.frames_alocados)
        pool.sort()
        processo.frames_alocados = []

    @staticmethod
    def simular_lru(string_referencia, num_frames):
        """
        Executa a string de referencia aplicando LRU local e devolve o
        numero de faltas de pagina.

        Convencao de pre-carga: a PRIMEIRA pagina referenciada e carregada
        antecipadamente (pre-carga de 1 pagina) e, portanto, nao e
        contabilizada como falta.

        A lista 'residentes' guarda as paginas em memoria em ordem de uso:
        a posicao 0 e a menos recentemente usada (candidata a substituicao)
        e a ultima posicao e a mais recentemente usada.
        """
        residentes = []
        faltas = 0

        for indice, pagina in enumerate(string_referencia):
            if pagina in residentes:
                # Acerto: atualiza a "idade" movendo a pagina para o fim (MRU).
                residentes.remove(pagina)
                residentes.append(pagina)
                continue

            # Falta de pagina.
            if indice == 0:
                # Pre-carga da primeira pagina: nao conta como falta.
                residentes.append(pagina)
                continue

            faltas += 1
            if len(residentes) >= num_frames:
                # Memoria cheia: remove a pagina menos recentemente usada.
                residentes.pop(0)
            residentes.append(pagina)

        return faltas
