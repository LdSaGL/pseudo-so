"""
Modulo de Leitura das Entradas.

Faz o parsing dos tres arquivos .txt de entrada:
  1. processes.txt -> lista de Processo
  2. files.txt     -> configuracao do disco e operacoes de arquivo
  3. string.txt    -> string de referencia de paginas de cada processo
"""

from processo import Processo


def _campos(linha):
    """Quebra uma linha em campos separados por virgula, sem espacos."""
    return [c.strip() for c in linha.strip().split(",") if c.strip() != ""]


def ler_processos(caminho):
    """
    Le processes.txt. Cada linha vira um Processo com PID sequencial (0..N-1).

    Formato de cada linha:
    <t_inicializacao>, <prioridade>, <t_processador>, <working_set>,
    <impressora>, <scanner>, <modem>, <sata>
    """
    processos = []
    with open(caminho, "r") as arquivo:
        pid = 0
        for linha in arquivo:
            if linha.strip() == "":
                continue
            dados = _campos(linha)
            processo = Processo(
                pid=pid,
                tempo_inicializacao=int(dados[0]),
                prioridade=int(dados[1]),
                tempo_processador=int(dados[2]),
                tamanho_working_set=int(dados[3]),
                usa_impressora=int(dados[4]),
                usa_scanner=int(dados[5]),
                usa_modem=int(dados[6]),
                usa_sata=int(dados[7]),
            )
            processos.append(processo)
            pid += 1
    return processos


def ler_strings_referencia(caminho, processos):
    """
    Le string.txt. A linha i contem a string de referencia do processo i.
    """
    with open(caminho, "r") as arquivo:
        linhas = [l for l in arquivo if l.strip() != ""]
    for indice, linha in enumerate(linhas):
        if indice < len(processos):
            paginas = [int(p) for p in _campos(linha)]
            processos[indice].string_referencia = paginas


def ler_arquivos(caminho):
    """
    Le files.txt e devolve (total_blocos, preexistentes, operacoes).

    - total_blocos : quantidade total de blocos do disco.
    - preexistentes: lista de (nome, primeiro_bloco, quantidade_blocos).
    - operacoes    : lista de dicts com pid, codigo (0=criar, 1=deletar),
                     nome e blocos (apenas para criacao).
    """
    with open(caminho, "r") as arquivo:
        linhas = [l for l in arquivo if l.strip() != ""]

    total_blocos = int(linhas[0].strip())
    qtd_segmentos = int(linhas[1].strip())

    preexistentes = []
    for i in range(2, 2 + qtd_segmentos):
        dados = _campos(linhas[i])
        nome = dados[0]
        primeiro_bloco = int(dados[1])
        quantidade = int(dados[2])
        preexistentes.append((nome, primeiro_bloco, quantidade))

    operacoes = []
    for i in range(2 + qtd_segmentos, len(linhas)):
        dados = _campos(linhas[i])
        operacao = {
            "pid": int(dados[0]),
            "codigo": int(dados[1]),
            "nome": dados[2],
            # A quantidade de blocos so existe na operacao de criacao (codigo 0)
            "blocos": int(dados[3]) if len(dados) > 3 else None,
        }
        operacoes.append(operacao)

    return total_blocos, preexistentes, operacoes
