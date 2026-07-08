"""
Modulo de Processos.

Contem a classe Processo, que funciona como o PCB (Process Control Block)
do pseudo-SO: guarda as informacoes estaticas lidas do arquivo de entrada
e o estado dinamico do processo durante a execucao.
"""


class Processo:
    """Representa um processo gerenciado pelo pseudo-SO."""

    def __init__(self, pid, tempo_inicializacao, prioridade, tempo_processador,
                 tamanho_working_set, usa_impressora, usa_scanner, usa_modem,
                 usa_sata):
        # ---- Informacoes estaticas (vindas do processes.txt) ----
        self.pid = pid                                  # identificador (0..N-1)
        self.tempo_inicializacao = tempo_inicializacao  # instante de chegada
        self.prioridade = prioridade                    # 0 = tempo real; 1..3 = usuario
        self.tempo_processador = tempo_processador      # total de instrucoes (quantum)
        self.tamanho_working_set = tamanho_working_set  # nro maximo de frames

        # Requisicoes de recursos de E/S (0 ou 1)
        self.usa_impressora = usa_impressora
        self.usa_scanner = usa_scanner
        self.usa_modem = usa_modem
        self.usa_sata = usa_sata

        # ---- Estado dinamico ----
        self.tempo_restante = tempo_processador   # quantum ainda a executar
        self.faltas_paginas = 0                   # page faults contabilizados
        self.string_referencia = []               # sequencia de paginas referenciadas
        self.frames_alocados = []                 # indices dos frames que o processo possui
        self.recursos_alocados = []               # nomes dos recursos de E/S em uso
        self.iniciado = False                     # ja imprimiu "STARTED"?
        self.prioridade_atual = prioridade        # prioridade dinamica (usada no aging)

    @property
    def eh_tempo_real(self):
        """Processos de tempo real tem prioridade 0."""
        return self.prioridade == 0

    @property
    def terminou(self):
        return self.tempo_restante <= 0

    def requisita_algum_recurso(self):
        """Indica se o processo pediu ao menos um recurso de E/S."""
        return bool(self.usa_impressora or self.usa_scanner
                    or self.usa_modem or self.usa_sata)

    def __repr__(self):
        return "Processo(pid={}, prioridade={}, tempo={})".format(
            self.pid, self.prioridade, self.tempo_processador)
