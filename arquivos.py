"""
Modulo de Sistema de Arquivos.

Implementa um sistema de arquivos com ALOCACAO CONTIGUA. O disco e um vetor
de blocos; cada arquivo ocupa blocos consecutivos. A busca por espaco livre
usa o algoritmo FIRST-FIT, sempre a partir do primeiro bloco do disco.

Regras de permissao:
  - processos de tempo real podem criar (se houver espaco) e deletar QUALQUER
    arquivo, mesmo os que nao foram criados por eles;
  - processos de usuario podem criar quantos arquivos quiserem (se houver
    espaco) e so podem deletar arquivos criados por eles mesmos.
"""


class SistemaArquivos:
    """Gerencia o disco, os arquivos e as operacoes de criar/deletar."""

    def __init__(self, total_blocos):
        self.total_blocos = total_blocos
        # disco[i] = nome do arquivo que ocupa o bloco i, ou None se livre.
        self.disco = [None] * total_blocos
        # arquivos[nome] = {"inicio": int, "tamanho": int, "dono": pid ou None}
        self.arquivos = {}

    # ------------------------------------------------------------------ #
    # Configuracao inicial
    # ------------------------------------------------------------------ #
    def adicionar_preexistente(self, nome, inicio, tamanho):
        """
        Registra um arquivo ja gravado no disco na carga inicial.

        Valida a geometria do segmento antes de escrever: um segmento que
        comeca fora do disco, tem tamanho negativo ou ultrapassa o ultimo
        bloco e uma configuracao impossivel (analoga a pedir mais disco do
        que existe) e gera erro claro em vez de corromper o disco/estourar.
        """
        if inicio < 0 or tamanho < 0 or inicio + tamanho > self.total_blocos:
            raise ValueError(
                "Segmento pre-existente {} (inicio {}, tamanho {}) nao cabe "
                "no disco de {} blocos.".format(
                    nome, inicio, tamanho, self.total_blocos))
        for bloco in range(inicio, inicio + tamanho):
            if self.disco[bloco] is not None:
                raise ValueError(
                    "Segmento pre-existente {} sobrepoe o bloco {}, ja "
                    "ocupado por {}.".format(nome, bloco, self.disco[bloco]))
            self.disco[bloco] = nome
        self.arquivos[nome] = {"inicio": inicio, "tamanho": tamanho,
                               "dono": None}

    # ------------------------------------------------------------------ #
    # Algoritmo de alocacao
    # ------------------------------------------------------------------ #
    def _first_fit(self, tamanho):
        """
        Procura o primeiro espaco contiguo de 'tamanho' blocos livres.
        Retorna o indice do primeiro bloco, ou None se nao couber.
        """
        contador = 0
        inicio = 0
        for bloco in range(self.total_blocos):
            if self.disco[bloco] is None:
                if contador == 0:
                    inicio = bloco
                contador += 1
                if contador == tamanho:
                    return inicio
            else:
                contador = 0
        return None

    @staticmethod
    def _formatar_blocos(inicio, tamanho):
        """Formata a lista de blocos no estilo 'blocos 0, 1 e 2'."""
        blocos = [str(b) for b in range(inicio, inicio + tamanho)]
        if len(blocos) == 1:
            return "bloco " + blocos[0]
        return "blocos " + ", ".join(blocos[:-1]) + " e " + blocos[-1]

    # ------------------------------------------------------------------ #
    # Operacoes
    # ------------------------------------------------------------------ #
    def criar(self, processo, nome, tamanho):
        """
        Cria um arquivo de 'tamanho' blocos usando first-fit.
        Retorna (sucesso, mensagem).
        """
        # Nao permite dois arquivos com o mesmo nome no disco.
        if nome in self.arquivos:
            return (False,
                    "O processo {} não pode criar o arquivo {} "
                    "porque já existe um arquivo com esse nome.".format(
                        processo.pid, nome))

        inicio = self._first_fit(tamanho)
        if inicio is None:
            return (False,
                    "O processo {} não pode criar o arquivo {} "
                    "(falta de espaço).".format(processo.pid, nome))

        for bloco in range(inicio, inicio + tamanho):
            self.disco[bloco] = nome
        self.arquivos[nome] = {"inicio": inicio, "tamanho": tamanho,
                               "dono": processo.pid}
        return (True,
                "O processo {} criou o arquivo {} ({}).".format(
                    processo.pid, nome, self._formatar_blocos(inicio, tamanho)))

    def deletar(self, processo, nome):
        """
        Deleta um arquivo respeitando as permissoes.
        Retorna (sucesso, mensagem).
        """
        if nome not in self.arquivos:
            return (False,
                    "O processo {} não pode deletar o arquivo {} "
                    "porque ele não existe.".format(processo.pid, nome))

        dono = self.arquivos[nome]["dono"]
        # Usuario comum so pode deletar arquivos criados por ele mesmo.
        if not processo.eh_tempo_real and dono != processo.pid:
            return (False,
                    "O processo {} não pode deletar o arquivo {} "
                    "porque não foi ele quem o criou.".format(
                        processo.pid, nome))

        inicio = self.arquivos[nome]["inicio"]
        tamanho = self.arquivos[nome]["tamanho"]
        for bloco in range(inicio, inicio + tamanho):
            self.disco[bloco] = None
        del self.arquivos[nome]
        return (True, "O processo {} deletou o arquivo {}.".format(
            processo.pid, nome))

    # ------------------------------------------------------------------ #
    # Saida
    # ------------------------------------------------------------------ #
    def mapa_ocupacao(self):
        """Devolve o mapa do disco: nome do arquivo por bloco, 0 se vazio."""
        return [bloco if bloco is not None else "0" for bloco in self.disco]
