"""
Modulo de Filas.

Mantem a estrutura de filas de prontos do pseudo-SO:

  - 1 fila de TEMPO REAL (prioridade 0), escalonada por FIFO sem preempcao;
  - 3 filas de USUARIO (prioridades 1, 2 e 3), formando um esquema de
    Multiplas Filas com Realimentacao (MLFQ).

Regras:
  - menor valor de prioridade = maior prioridade de escalonamento;
  - processos de usuario sofrem preempcao (quantum) e, ao gastarem um
    quantum, sao rebaixados para a fila imediatamente inferior (feedback);
  - para evitar starvation, aplica-se envelhecimento (aging): processos que
    esperam ha muito tempo sao promovidos para uma fila de maior prioridade.
"""

from collections import deque


class GerenciadorFilas:
    """Encapsula a fila de tempo real e as 3 filas de usuario."""

    NUM_FILAS_USUARIO = 3          # prioridades 1, 2 e 3
    LIMITE_ENVELHECIMENTO = 5      # quanto de espera para promover (aging)

    def __init__(self):
        self.fila_tempo_real = deque()
        # Indice 0 -> prioridade 1; indice 1 -> prioridade 2; indice 2 -> prioridade 3
        self.filas_usuario = [deque() for _ in range(self.NUM_FILAS_USUARIO)]
        # Tempo de espera acumulado de cada processo, para o aging.
        self.espera = {}

    # ------------------------------------------------------------------ #
    # Insercao
    # ------------------------------------------------------------------ #
    def inserir(self, processo):
        """Coloca o processo na fila correta conforme a prioridade atual."""
        self.espera.setdefault(processo.pid, 0)
        if processo.eh_tempo_real:
            self.fila_tempo_real.append(processo)
        else:
            indice = self._indice_fila(processo.prioridade_atual)
            self.filas_usuario[indice].append(processo)

    def _indice_fila(self, prioridade):
        """Converte prioridade (1..3) em indice de lista (0..2)."""
        return max(0, min(self.NUM_FILAS_USUARIO - 1, prioridade - 1))

    # ------------------------------------------------------------------ #
    # Selecao do proximo processo
    # ------------------------------------------------------------------ #
    def ha_tempo_real(self):
        return len(self.fila_tempo_real) > 0

    def proximo_tempo_real(self):
        """Retira o proximo processo de tempo real (FIFO)."""
        return self.fila_tempo_real.popleft()

    def proximo_usuario(self):
        """
        Retira o proximo processo de usuario da fila de maior prioridade
        que estiver ocupada. Retorna None se nao houver nenhum.
        """
        for fila in self.filas_usuario:
            if fila:
                return fila.popleft()
        return None

    def ha_usuario(self):
        return any(self.filas_usuario)

    def vazio(self):
        return not self.ha_tempo_real() and not self.ha_usuario()

    # ------------------------------------------------------------------ #
    # Realimentacao (feedback) e envelhecimento (aging)
    # ------------------------------------------------------------------ #
    def rebaixar(self, processo):
        """
        Rebaixa um processo de usuario apos gastar seu quantum, movendo-o
        para a fila imediatamente inferior (ate a prioridade 3).
        """
        if processo.prioridade_atual < self.NUM_FILAS_USUARIO:
            processo.prioridade_atual += 1
        self.espera[processo.pid] = 0
        self.inserir(processo)

    def envelhecer(self, processo_em_execucao):
        """
        Aplica aging: incrementa a espera dos processos de usuario que estao
        aguardando e promove os que ultrapassaram o limite, prevenindo
        starvation.
        """
        for indice in range(self.NUM_FILAS_USUARIO - 1, 0, -1):
            promovidos = []
            for processo in list(self.filas_usuario[indice]):
                self.espera[processo.pid] += 1
                if self.espera[processo.pid] >= self.LIMITE_ENVELHECIMENTO:
                    promovidos.append(processo)
            for processo in promovidos:
                self.filas_usuario[indice].remove(processo)
                processo.prioridade_atual -= 1
                self.espera[processo.pid] = 0
                self.filas_usuario[indice - 1].append(processo)
