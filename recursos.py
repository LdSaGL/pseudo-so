"""
Modulo de Recursos de E/S.

Gerencia a alocacao exclusiva dos dispositivos de E/S:
  - 1 scanner
  - 2 impressoras
  - 1 modem
  - 2 dispositivos SATA

Regras:
  - cada recurso e alocado a um processo por vez (exclusao mutua);
  - nao ha preempcao na alocacao dos dispositivos;
  - processos de tempo real NAO utilizam recursos de E/S.

A exclusao mutua e representada por uma classe Semaforo. Como a simulacao
roda em fluxo unico, o semaforo aqui documenta e garante a regra de uso
exclusivo (P/wait antes de usar, V/signal ao liberar); em uma versao com
threads reais, seria o mesmo mecanismo de sincronizacao.
"""


class Semaforo:
    """Semaforo contador classico (operacoes wait/signal)."""

    def __init__(self, valor_inicial):
        self.valor = valor_inicial

    def disponivel(self):
        return self.valor > 0

    def wait(self):
        """Operacao P: tenta adquirir uma unidade do recurso."""
        if self.valor > 0:
            self.valor -= 1
            return True
        return False

    def signal(self):
        """Operacao V: libera uma unidade do recurso."""
        self.valor += 1


class GerenciadorRecursos:
    """Controla os semaforos de cada tipo de dispositivo de E/S."""

    def __init__(self):
        self.semaforos = {
            "scanner": Semaforo(1),
            "impressora": Semaforo(2),
            "modem": Semaforo(1),
            "sata": Semaforo(2),
        }

    def _requisitados(self, processo):
        """Lista os recursos pedidos pelo processo (conforme as flags)."""
        pedidos = []
        if processo.usa_impressora:
            pedidos.append("impressora")
        if processo.usa_scanner:
            pedidos.append("scanner")
        if processo.usa_modem:
            pedidos.append("modem")
        if processo.usa_sata:
            pedidos.append("sata")
        return pedidos

    def pode_alocar(self, processo):
        """Verifica se TODOS os recursos pedidos estao disponiveis."""
        if processo.eh_tempo_real:
            return True  # tempo real nao usa E/S
        return all(self.semaforos[r].disponivel()
                   for r in self._requisitados(processo))

    def alocar(self, processo):
        """
        Aloca de forma atomica todos os recursos pedidos pelo processo.
        Retorna True se conseguiu; False se algum estava indisponivel
        (nesse caso nada e alocado, evitando alocacao parcial/deadlock).
        """
        if processo.eh_tempo_real:
            return True
        pedidos = self._requisitados(processo)
        if not all(self.semaforos[r].disponivel() for r in pedidos):
            return False
        for recurso in pedidos:
            self.semaforos[recurso].wait()
            processo.recursos_alocados.append(recurso)
        return True

    def liberar(self, processo):
        """Libera todos os recursos que o processo mantinha."""
        for recurso in processo.recursos_alocados:
            self.semaforos[recurso].signal()
        processo.recursos_alocados = []
