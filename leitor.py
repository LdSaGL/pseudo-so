"""
Modulo de Leitura das Entradas.

Faz o parsing dos tres arquivos .txt de entrada:
  1. processes.txt -> lista de Processo
  2. files.txt     -> configuracao do disco e operacoes de arquivo
  3. string.txt    -> string de referencia de paginas de cada processo

Politica de robustez: o parsing NUNCA aborta a simulacao. Linhas invalidas
sao ignoradas (ou viram operacoes que falham), com um aviso impresso em
stderr. O stdout fica reservado exclusivamente para a saida no formato do
enunciado, que sera comparada com a implementacao de referencia — abortar
no meio perderia todos os casos que responderiam corretamente.
"""

import sys

from processo import Processo


def _aviso(mensagem):
    """Imprime um diagnostico em stderr (stdout fica so com a saida oficial)."""
    print("[aviso] {}".format(mensagem), file=sys.stderr)


def _campos(linha):
    """Quebra uma linha em campos separados por virgula, sem espacos."""
    return [c.strip() for c in linha.strip().split(",") if c.strip() != ""]


def _inteiro_ou_none(texto):
    """Converte para int; devolve None se o texto nao for um inteiro."""
    try:
        return int(texto)
    except ValueError:
        return None


def _linhas_nao_vazias(caminho):
    """
    Le o arquivo e devolve pares (numero_da_linha, texto) nao vazios.
    'utf-8-sig' descarta o BOM se existir; strip() cobre finais CRLF.
    """
    with open(caminho, "r", encoding="utf-8-sig") as arquivo:
        return [(numero, linha)
                for numero, linha in enumerate(arquivo, start=1)
                if linha.strip() != ""]


def ler_processos(caminho):
    """
    Le processes.txt. Cada linha vira um Processo com PID sequencial (0..N-1).

    Formato de cada linha (8 campos inteiros):
    <t_inicializacao>, <prioridade>, <t_processador>, <working_set>,
    <impressora>, <scanner>, <modem>, <sata>

    Linha invalida: e ignorada com aviso, mas o PID daquela posicao e
    RESERVADO (nao reutilizado), para que os demais processos mantenham os
    mesmos PIDs que teriam com o arquivo integro.
    """
    processos = []
    pid = 0
    for numero, linha in _linhas_nao_vazias(caminho):
        dados = _campos(linha)
        valores = [_inteiro_ou_none(c) for c in dados]
        if len(valores) != 8 or any(v is None for v in valores):
            _aviso("processes.txt linha {}: esperados 8 campos inteiros, "
                   "encontrado '{}'; processo PID {} ignorado.".format(
                       numero, linha.strip(), pid))
            pid += 1
            continue
        processos.append(Processo(
            pid=pid,
            tempo_inicializacao=valores[0],
            prioridade=valores[1],
            tempo_processador=valores[2],
            tamanho_working_set=valores[3],
            usa_impressora=valores[4],
            usa_scanner=valores[5],
            usa_modem=valores[6],
            usa_sata=valores[7],
        ))
        pid += 1
    return processos


def ler_strings_referencia(caminho, processos):
    """
    Le string.txt. A i-esima linha nao vazia contem a string de referencia do
    processo de PID i (associacao pela posicao da linha, como no enunciado).

    Tokens nao inteiros sao ignorados com aviso; divergencia entre o numero
    de linhas e o de processos gera aviso (as strings ausentes ficam vazias,
    resultando em 0 faltas para aqueles processos).
    """
    linhas = _linhas_nao_vazias(caminho)
    por_pid = {p.pid: p for p in processos}
    total_esperado = (max(por_pid) + 1) if por_pid else 0
    if len(linhas) < total_esperado:
        _aviso("string.txt tem {} linha(s) para {} processo(s); os processos "
               "sem linha ficam sem referencia (0 faltas).".format(
                   len(linhas), total_esperado))
    elif len(linhas) > total_esperado:
        _aviso("string.txt tem {} linha(s) para {} processo(s); as linhas "
               "extras serao ignoradas.".format(len(linhas), total_esperado))

    for indice, (numero, linha) in enumerate(linhas):
        processo = por_pid.get(indice)
        if processo is None:
            continue
        paginas = []
        for token in _campos(linha):
            valor = _inteiro_ou_none(token)
            if valor is None:
                _aviso("string.txt linha {}: pagina '{}' ignorada "
                       "(nao e um inteiro).".format(numero, token))
            else:
                paginas.append(valor)
        processo.string_referencia = paginas


def _ler_operacao(numero, dados):
    """
    Interpreta uma linha de operacao. Devolve o dict da operacao; se a linha
    for invalida, devolve uma operacao marcada como 'invalida' com o motivo
    (ela vira 'Operação N => Falha' na saida, preservando a numeracao das
    operacoes seguintes).
    """
    def invalida(motivo):
        return {"invalida": True,
                "motivo": "Operação inválida (files.txt linha {}): {}.".format(
                    numero, motivo)}

    if len(dados) < 3:
        return invalida("esperados ao menos 3 campos (pid, codigo, nome)")
    pid = _inteiro_ou_none(dados[0])
    if pid is None:
        return invalida("pid '{}' nao e um inteiro".format(dados[0]))
    codigo = _inteiro_ou_none(dados[1])
    if codigo is None:
        return invalida("codigo '{}' nao e um inteiro".format(dados[1]))
    if codigo not in (0, 1):
        return invalida("codigo {} desconhecido; use 0 (criar) "
                        "ou 1 (deletar)".format(codigo))

    blocos = None
    if codigo == 0:                       # criacao exige o numero de blocos
        if len(dados) < 4:
            return invalida("criacao (codigo 0) exige o numero de blocos")
        blocos = _inteiro_ou_none(dados[3])
        if blocos is None:
            return invalida("numero de blocos '{}' nao e um inteiro".format(
                dados[3]))
        if blocos <= 0:
            return invalida("numero de blocos deve ser positivo "
                            "(encontrado {})".format(blocos))
    return {"pid": pid, "codigo": codigo, "nome": dados[2], "blocos": blocos}


def ler_arquivos(caminho):
    """
    Le files.txt e devolve (total_blocos, preexistentes, operacoes).

    Formato:
      Linha 1: total de blocos do disco (inteiro positivo).
      Linha 2: quantidade n de segmentos pre-existentes (inteiro >= 0).
      Linhas 3..n+2: <nome>, <primeiro_bloco>, <qtd_blocos>.
      Linhas seguintes: <pid>, <codigo>, <nome>[, <blocos>]
        - codigo 0 = criar (exige <blocos>); codigo 1 = deletar.

    Cabecalho ilegivel degrada o sistema de arquivos (0 blocos, sem
    operacoes) com aviso, mas a simulacao dos processos segue normalmente.
    """
    linhas = _linhas_nao_vazias(caminho)
    if not linhas:
        _aviso("files.txt vazio; sistema de arquivos desabilitado.")
        return 0, [], []

    total_blocos = _inteiro_ou_none(linhas[0][1].strip())
    if total_blocos is None or total_blocos < 0:
        _aviso("files.txt linha {}: total de blocos invalido ('{}'); "
               "sistema de arquivos desabilitado.".format(
                   linhas[0][0], linhas[0][1].strip()))
        return 0, [], []

    if len(linhas) < 2:
        _aviso("files.txt: linha da quantidade de segmentos ausente; "
               "assumindo 0 segmentos e nenhuma operacao.")
        return total_blocos, [], []

    qtd_segmentos = _inteiro_ou_none(linhas[1][1].strip())
    if qtd_segmentos is None or qtd_segmentos < 0:
        _aviso("files.txt linha {}: quantidade de segmentos invalida ('{}'); "
               "assumindo 0.".format(linhas[1][0], linhas[1][1].strip()))
        qtd_segmentos = 0

    # Segmentos pre-existentes: <nome>, <inicio:int>, <tamanho:int>.
    preexistentes = []
    indice = 2
    restantes = qtd_segmentos
    while restantes > 0 and indice < len(linhas):
        numero, linha = linhas[indice]
        dados = _campos(linha)
        inicio = _inteiro_ou_none(dados[1]) if len(dados) == 3 else None
        tamanho = _inteiro_ou_none(dados[2]) if len(dados) == 3 else None
        if inicio is None or tamanho is None:
            _aviso("files.txt linha {}: esperado segmento pre-existente "
                   "(nome, inicio, tamanho); tratando desta linha em diante "
                   "como operacoes.".format(numero))
            break
        preexistentes.append((dados[0], inicio, tamanho))
        indice += 1
        restantes -= 1
    if restantes > 0 and indice >= len(linhas):
        _aviso("files.txt: declarados {} segmento(s) pre-existente(s), mas "
               "so {} foram encontrados.".format(
                   qtd_segmentos, len(preexistentes)))

    operacoes = [_ler_operacao(numero, _campos(linha))
                 for numero, linha in linhas[indice:]]
    return total_blocos, preexistentes, operacoes
