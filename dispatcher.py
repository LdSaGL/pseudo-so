"""
Pseudo-SO multiprogramado - Processo Despachante (dispatcher).

Este e o processo principal do pseudo-SO. Ele:
  1. le os tres arquivos de entrada (processos, arquivos e strings);
  2. escalona a CPU entre os processos (tempo real FIFO + usuario MLFQ);
  3. executa as operacoes do sistema de arquivos;
  4. imprime o mapa de ocupacao do disco e as faltas de pagina.

Uso:
    python3 dispatcher.py <processes.txt> <files.txt> <string.txt>

Implementado usando apenas a biblioteca padrao do Python 3.
"""

import sys

from leitor import ler_processos, ler_strings_referencia, ler_arquivos
from memoria import GerenciadorMemoria
from recursos import GerenciadorRecursos
from filas import GerenciadorFilas
from arquivos import SistemaArquivos


# ---------------------------------------------------------------------- #
# Impressao (formato definido no enunciado)
# ---------------------------------------------------------------------- #
def imprimir_bloco_dispatcher(processo):
    """Imprime o bloco de identificacao do processo cedido pela CPU."""
    print("dispatcher =>")
    print(" PID: {}".format(processo.pid))
    print(" frames: {}".format(processo.tamanho_working_set))
    print(" priority: {}".format(processo.prioridade))
    print(" time: {}".format(processo.tempo_processador))
    print(" printers: {}".format(processo.usa_impressora))
    print(" scanners: {}".format(processo.usa_scanner))
    print(" modems: {}".format(processo.usa_modem))
    print(" drives: {}".format(processo.usa_sata))
    print()


def executar(processo, quantum):
    """
    Simula a execucao do processo por 'quantum' instrucoes, imprimindo as
    mensagens de execucao. Imprime STARTED na primeira vez e return SIGINT
    quando o processo termina.
    """
    print("process {} =>".format(processo.pid))
    if not processo.iniciado:
        print("P{} STARTED".format(processo.pid))
        processo.iniciado = True

    ja_executadas = processo.tempo_processador - processo.tempo_restante
    for _ in range(quantum):
        ja_executadas += 1
        print("P{} instruction {}".format(processo.pid, ja_executadas))

    processo.tempo_restante -= quantum
    if processo.terminou:
        print("P{} return SIGINT".format(processo.pid))
    print()


# ---------------------------------------------------------------------- #
# Admissao
# ---------------------------------------------------------------------- #
def _aviso(mensagem):
    """Diagnostico em stderr; o stdout fica so com a saida do enunciado."""
    print("[aviso] {}".format(mensagem), file=sys.stderr)


def admitir_ou_rejeitar(processo, memoria):
    """
    Verifica se um processo recem-selecionado pode ser admitido.

    Retorna False (com o motivo avisado em stderr) quando o processo e
    impossivel de executar e deve ser descartado em vez de reenfileirado,
    evitando que o escalonador entre em laco infinito. Sao dois casos:

      - working set invalido ou maior que toda a area de memoria da classe
        (jamais havera frames suficientes, mesmo com a memoria vazia);
      - tempo de processador nao positivo (nao ha instrucoes a executar).

    O aviso vai para stderr para nao poluir o stdout comparado com a
    referencia. Processos validos retornam True e seguem o fluxo normal.
    """
    motivo = None
    if processo.tamanho_working_set <= 0:
        motivo = ("working set invalido ({}); precisa de ao menos 1 frame"
                  .format(processo.tamanho_working_set))
    elif not memoria.cabe_na_area(processo):
        motivo = ("working set ({}) excede a memoria da area"
                  .format(processo.tamanho_working_set))
    elif processo.tempo_processador <= 0:
        motivo = ("sem instrucoes a executar (tempo {})"
                  .format(processo.tempo_processador))
    if motivo is not None:
        _aviso("P{} rejeitado: {}".format(processo.pid, motivo))
        return False
    return True


# ---------------------------------------------------------------------- #
# Escalonador
# ---------------------------------------------------------------------- #
def escalonar(processos, memoria, recursos, filas):
    """
    Loop principal do escalonador.

    - Processos de tempo real: fila FIFO, executados ate o fim SEM preempcao.
    - Processos de usuario: MLFQ com quantum de 1 (preempcao), rebaixamento
      apos gastar o quantum (feedback) e envelhecimento (aging).
    - Um processo de usuario que nao pode iniciar por falta de memoria/E/S vai
      para o estado BLOQUEADO (sai da fila de prontos) em vez de ser
      reescolhido em busy-wait; volta a competir quando outro processo termina
      e libera os recursos.
    """
    nao_admitidos = sorted(processos,
                           key=lambda p: (p.tempo_inicializacao, p.pid))
    tempo = 0
    total = len(processos)
    finalizados = 0

    def pode_rodar(processo):
        """O processo tem memoria e recursos de E/S disponiveis agora?"""
        return memoria.tem_espaco(processo) and recursos.pode_alocar(processo)

    while finalizados < total:
        # Admite os processos que ja chegaram (tempo de inicializacao <= tempo).
        while nao_admitidos and nao_admitidos[0].tempo_inicializacao <= tempo:
            filas.inserir(nao_admitidos.pop(0))

        # Se nao ha ninguem pronto, avanca o relogio ate a proxima chegada.
        if filas.vazio():
            if nao_admitidos:
                tempo = nao_admitidos[0].tempo_inicializacao
                continue
            break

        # Prioridade absoluta para tempo real (FIFO, sem preempcao).
        if filas.ha_tempo_real():
            processo = filas.proximo_tempo_real()
            if not admitir_ou_rejeitar(processo, memoria):
                finalizados += 1
                continue
            memoria.alocar(processo)
            processo.faltas_paginas = GerenciadorMemoria.simular_lru(
                processo.string_referencia, processo.tamanho_working_set)
            imprimir_bloco_dispatcher(processo)
            executar(processo, processo.tempo_restante)  # roda ate terminar
            memoria.liberar(processo)
            finalizados += 1
            tempo += processo.tempo_processador
            continue

        # Processos de usuario: MLFQ com quantum de 1.
        processo = filas.proximo_usuario()

        # Admissao: descarta processos impossiveis de carregar (working set
        # maior que a area de memoria) ou sem instrucoes a executar.
        if not admitir_ou_rejeitar(processo, memoria):
            finalizados += 1
            continue

        # Na primeira execucao, garante memoria e recursos de E/S.
        if not processo.iniciado:
            if not pode_rodar(processo):
                # Sem recursos: BLOQUEIA (sai da fila de prontos). Nao consome
                # quantum nem avanca o relogio; volta quando algo for liberado.
                filas.bloquear(processo)
                continue
            memoria.alocar(processo)
            recursos.alocar(processo)
            processo.faltas_paginas = GerenciadorMemoria.simular_lru(
                processo.string_referencia, processo.tamanho_working_set)

        imprimir_bloco_dispatcher(processo)
        executar(processo, 1)                # 1 quantum
        tempo += 1

        if processo.terminou:
            recursos.liberar(processo)
            memoria.liberar(processo)
            finalizados += 1
            # Recursos liberados: reavalia quem estava bloqueado e devolve a
            # fila de prontos os que agora podem rodar.
            filas.desbloquear(pode_rodar)
        else:
            filas.rebaixar(processo)         # realimentacao (feedback)
        filas.envelhecer(processo)           # envelhecimento (aging)


# ---------------------------------------------------------------------- #
# Sistema de arquivos
# ---------------------------------------------------------------------- #
def executar_operacoes(operacoes, sistema_arquivos, processos):
    """Executa, em ordem, as operacoes de criacao/remocao de arquivos."""
    print("Sistema de arquivos =>")
    print()

    por_pid = {p.pid: p for p in processos}
    for numero, operacao in enumerate(operacoes, start=1):
        if operacao.get("invalida"):
            # Linha malformada no files.txt: falha a operacao com o motivo,
            # preservando a numeracao das operacoes seguintes.
            sucesso = False
            mensagem = operacao["motivo"]
        elif operacao["pid"] not in por_pid:
            sucesso = False
            mensagem = "O processo {} não existe.".format(operacao["pid"])
        else:
            processo = por_pid[operacao["pid"]]
            if operacao["codigo"] == 0:      # criar
                sucesso, mensagem = sistema_arquivos.criar(
                    processo, operacao["nome"], operacao["blocos"])
            else:                            # deletar
                sucesso, mensagem = sistema_arquivos.deletar(
                    processo, operacao["nome"])

        rotulo = "Sucesso" if sucesso else "Falha"
        print("Operação {} => {}".format(numero, rotulo))
        print(mensagem)
        print()


def imprimir_mapa(sistema_arquivos):
    """Imprime o mapa de ocupacao do disco (0 = bloco vazio)."""
    print("Mapa de ocupação do disco:")
    print(" ".join(sistema_arquivos.mapa_ocupacao()))
    print()


def imprimir_faltas(processos):
    """Imprime o numero de faltas de pagina de cada processo."""
    print("Número de Faltas de Páginas por processo:")
    for processo in processos:
        print("P{} = {} faltas de páginas".format(
            processo.pid, processo.faltas_paginas))


# ---------------------------------------------------------------------- #
# Programa principal
# ---------------------------------------------------------------------- #
def main():
    if len(sys.argv) != 4:
        print("Uso: python3 dispatcher.py <processes.txt> <files.txt> "
              "<string.txt>")
        return

    caminho_processos = sys.argv[1]
    caminho_arquivos = sys.argv[2]
    caminho_strings = sys.argv[3]

    # Leitura das entradas. O leitor ja tolera linhas invalidas (avisa em
    # stderr); aqui tratamos apenas arquivos ilegiveis, degradando para o
    # vazio em vez de abortar: a simulacao SEMPRE roda ate o fim, pois a
    # saida sera comparada integralmente com a referencia.
    processos = []
    try:
        processos = ler_processos(caminho_processos)
    except OSError as erro:
        _aviso("nao foi possivel ler '{}': {}".format(caminho_processos, erro))
    try:
        ler_strings_referencia(caminho_strings, processos)
    except OSError as erro:
        _aviso("nao foi possivel ler '{}': {}".format(caminho_strings, erro))
    total_blocos, preexistentes, operacoes = 0, [], []
    try:
        total_blocos, preexistentes, operacoes = ler_arquivos(caminho_arquivos)
    except OSError as erro:
        _aviso("nao foi possivel ler '{}': {}".format(caminho_arquivos, erro))

    # Gerenciadores.
    memoria = GerenciadorMemoria()
    recursos = GerenciadorRecursos()
    filas = GerenciadorFilas()
    sistema_arquivos = SistemaArquivos(total_blocos)
    for nome, inicio, tamanho in preexistentes:
        try:
            sistema_arquivos.adicionar_preexistente(nome, inicio, tamanho)
        except ValueError as erro:
            # Segmento impossivel (fora do disco, sobreposto ou duplicado):
            # ignora SO o segmento e segue com o restante da simulacao.
            _aviso("segmento pre-existente ignorado: {}".format(erro))

    # Execucao.
    escalonar(processos, memoria, recursos, filas)
    executar_operacoes(operacoes, sistema_arquivos, processos)
    imprimir_mapa(sistema_arquivos)
    imprimir_faltas(processos)


if __name__ == "__main__":
    main()
