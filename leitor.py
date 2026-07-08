"""
Modulo de Leitura das Entradas.

Faz o parsing dos tres arquivos .txt de entrada:
  1. processes.txt -> lista de Processo
  2. files.txt     -> configuracao do disco e operacoes de arquivo
  3. string.txt    -> string de referencia de paginas de cada processo

Cada funcao valida o FORMATO da entrada (quantidade de campos, valores
inteiros, consistencia dos contadores) e levanta ValueError com uma
mensagem clara (incluindo o numero da linha) em vez de estourar com um
IndexError/ValueError cru do Python. A validacao da GEOMETRIA do disco
(segmento cabe no disco, sem sobreposicao) fica no modulo de arquivos.
"""

from processo import Processo


def _campos(linha):
    """Quebra uma linha em campos separados por virgula, sem espacos."""
    return [c.strip() for c in linha.strip().split(",") if c.strip() != ""]


def _inteiro(valor, contexto):
    """Converte 'valor' para int ou levanta ValueError com contexto claro."""
    try:
        return int(valor)
    except ValueError:
        raise ValueError(
            "{}: valor inteiro esperado, encontrado '{}'.".format(
                contexto, valor))


def _linhas_nao_vazias(caminho):
    """Le o arquivo e devolve pares (numero_da_linha, texto) nao vazios."""
    with open(caminho, "r") as arquivo:
        return [(numero, linha)
                for numero, linha in enumerate(arquivo, start=1)
                if linha.strip() != ""]


def ler_processos(caminho):
    """
    Le processes.txt. Cada linha vira um Processo com PID sequencial (0..N-1).

    Formato de cada linha (8 campos):
    <t_inicializacao>, <prioridade>, <t_processador>, <working_set>,
    <impressora>, <scanner>, <modem>, <sata>
    """
    processos = []
    pid = 0
    for numero, linha in _linhas_nao_vazias(caminho):
        dados = _campos(linha)
        if len(dados) != 8:
            raise ValueError(
                "processes.txt linha {}: esperados 8 campos "
                "(t_inicializacao, prioridade, t_processador, working_set, "
                "impressora, scanner, modem, sata), encontrados {}.".format(
                    numero, len(dados)))
        ctx = "processes.txt linha {}".format(numero)
        processo = Processo(
            pid=pid,
            tempo_inicializacao=_inteiro(dados[0], ctx + " (t_inicializacao)"),
            prioridade=_inteiro(dados[1], ctx + " (prioridade)"),
            tempo_processador=_inteiro(dados[2], ctx + " (t_processador)"),
            tamanho_working_set=_inteiro(dados[3], ctx + " (working_set)"),
            usa_impressora=_inteiro(dados[4], ctx + " (impressora)"),
            usa_scanner=_inteiro(dados[5], ctx + " (scanner)"),
            usa_modem=_inteiro(dados[6], ctx + " (modem)"),
            usa_sata=_inteiro(dados[7], ctx + " (sata)"),
        )
        processos.append(processo)
        pid += 1
    return processos


def ler_strings_referencia(caminho, processos):
    """
    Le string.txt. A i-esima linha nao vazia contem a string de referencia do
    processo i (associacao pela ordem). Cada campo deve ser um inteiro (numero
    da pagina logica acessada).
    """
    linhas = _linhas_nao_vazias(caminho)
    for indice, (numero, linha) in enumerate(linhas):
        if indice >= len(processos):
            break
        ctx = "string.txt linha {}".format(numero)
        processos[indice].string_referencia = [
            _inteiro(p, ctx) for p in _campos(linha)]


def ler_arquivos(caminho):
    """
    Le files.txt e devolve (total_blocos, preexistentes, operacoes).

    Formato:
      Linha 1: total de blocos do disco (inteiro positivo).
      Linha 2: quantidade n de segmentos pre-existentes (inteiro >= 0).
      Linhas 3..n+2: <nome>, <primeiro_bloco>, <qtd_blocos>.
      Linhas seguintes: <pid>, <codigo>, <nome>[, <blocos>]
        - codigo 0 = criar (exige <blocos>); codigo 1 = deletar.

    Retorno:
      - total_blocos : int.
      - preexistentes: lista de (nome, primeiro_bloco, qtd_blocos).
      - operacoes    : lista de dicts {"pid","codigo","nome","blocos"}
                       (blocos = None nas operacoes de delecao).
    """
    linhas = _linhas_nao_vazias(caminho)
    if len(linhas) < 2:
        raise ValueError(
            "files.txt: esperadas ao menos 2 linhas (total de blocos e "
            "quantidade de segmentos), encontradas {}.".format(len(linhas)))

    total_blocos = _inteiro(linhas[0][1].strip(),
                            "files.txt linha {} (total de blocos)".format(
                                linhas[0][0]))
    if total_blocos <= 0:
        raise ValueError(
            "files.txt linha {}: total de blocos deve ser positivo "
            "(encontrado {}).".format(linhas[0][0], total_blocos))

    qtd_segmentos = _inteiro(linhas[1][1].strip(),
                             "files.txt linha {} (qtd de segmentos)".format(
                                 linhas[1][0]))
    if qtd_segmentos < 0:
        raise ValueError(
            "files.txt linha {}: quantidade de segmentos nao pode ser "
            "negativa (encontrado {}).".format(linhas[1][0], qtd_segmentos))
    if len(linhas) < 2 + qtd_segmentos:
        raise ValueError(
            "files.txt: declarados {} segmentos pre-existentes, mas ha apenas "
            "{} linha(s) de segmento.".format(
                qtd_segmentos, len(linhas) - 2))

    preexistentes = []
    for i in range(2, 2 + qtd_segmentos):
        numero, linha = linhas[i]
        dados = _campos(linha)
        if len(dados) != 3:
            raise ValueError(
                "files.txt linha {}: segmento pre-existente exige 3 campos "
                "(nome, primeiro_bloco, qtd_blocos), encontrados {}.".format(
                    numero, len(dados)))
        ctx = "files.txt linha {}".format(numero)
        preexistentes.append((
            dados[0],
            _inteiro(dados[1], ctx + " (primeiro_bloco)"),
            _inteiro(dados[2], ctx + " (qtd_blocos)"),
        ))

    operacoes = []
    for i in range(2 + qtd_segmentos, len(linhas)):
        numero, linha = linhas[i]
        dados = _campos(linha)
        if len(dados) < 3:
            raise ValueError(
                "files.txt linha {}: operacao exige ao menos 3 campos "
                "(pid, codigo, nome), encontrados {}.".format(
                    numero, len(dados)))
        ctx = "files.txt linha {}".format(numero)
        codigo = _inteiro(dados[1], ctx + " (codigo)")
        if codigo not in (0, 1):
            raise ValueError(
                "files.txt linha {}: codigo de operacao invalido ({}); "
                "use 0 (criar) ou 1 (deletar).".format(numero, codigo))
        blocos = None
        if codigo == 0:                      # criacao exige o numero de blocos
            if len(dados) < 4:
                raise ValueError(
                    "files.txt linha {}: operacao de criacao (codigo 0) exige "
                    "o numero de blocos.".format(numero))
            blocos = _inteiro(dados[3], ctx + " (blocos)")
            if blocos <= 0:
                raise ValueError(
                    "files.txt linha {}: numero de blocos deve ser positivo "
                    "(encontrado {}).".format(numero, blocos))
        operacoes.append({
            "pid": _inteiro(dados[0], ctx + " (pid)"),
            "codigo": codigo,
            "nome": dados[2],
            "blocos": blocos,
        })

    return total_blocos, preexistentes, operacoes
