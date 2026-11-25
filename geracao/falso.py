"""Provedor de IA falso: respostas válidas e determinísticas, sem rede (LLM_PROVIDER=falso).

Serve para os testes e para ver o fluxo inteiro sem chave de API. O conteúdo é genérico,
mas respeita os schemas, as páginas de origem e as regras da aula.
"""
import json

from services.llm import RespostaLLM


class LLMFalso:
    nome = "falso"

    def __init__(self):
        self.chamadas = []

    def gerar_json(self, mensagens, schema, nome, contexto=None):
        contexto = contexto or {}
        self.chamadas.append(nome)
        dados = getattr(self, f"_{nome}")(contexto, mensagens)
        entrada = sum(len(m["content"]) for m in mensagens) // 4
        saida = len(json.dumps(dados, ensure_ascii=False)) // 4
        return RespostaLLM(dados, entrada, saida, "falso", 0.01)

    def _mapa(self, ctx, _):
        paginas = ctx.get("paginas") or [1]
        return {
            "temas": [{"nome": f"Tema das páginas {paginas[0]}-{paginas[-1]}", "resumo": "Resumo do tema.", "paginas": paginas}],
            "conceitos": [{"termo": "Conceito", "definicao": "Definição do material.", "paginas": paginas[:1]}],
            "glossario": [],
            "exemplos": [],
            "paginas_sem_conteudo": [],
        }

    def _ementa(self, ctx, _):
        paginas = ctx.get("paginas") or [1]
        n = max(1, min(ctx.get("n_modulos") or 2, 3))
        fatia = max(1, len(paginas) // (n * 2))
        modulos, i = [], 0
        for mi in range(1, n + 1):
            aulas = []
            for ai in range(1, 3):
                trecho = paginas[i:i + fatia] or paginas[-1:]
                i += fatia
                aulas.append({"titulo": f"Aula {mi}.{ai}", "objetivo": "Ao final, o aluno explica o tema.",
                              "paginas": trecho, "duracao_min": 12})
            modulos.append({"titulo": f"Módulo {mi}", "aulas": aulas})
        return {"titulo": "Curso de teste", "subtitulo": "Gerado sem IA", "descricao": "Descrição.",
                "categoria": "Teste", "modulos": modulos}

    def _aula(self, ctx, _):
        p = (ctx.get("paginas") or [1])[:2]
        slugs = ctx.get("slugs") or ["narrador"]
        mascote = slugs[1] if len(slugs) > 1 else slugs[0]
        titulo = ctx.get("titulo", "o tema")

        def bloco(tipo, config, roteiro="", titulo_bloco=""):
            return {"tipo": tipo, "titulo": titulo_bloco or tipo, "roteiro": roteiro, "texto_tela": "",
                    "config_json": json.dumps(config, ensure_ascii=False), "paginas_origem": p, "alem_do_pdf": False}

        questao = {"enunciado": "Qual a ideia central?", "alternativas": ["A certa", "Outra", "Mais uma", "Nenhuma"],
                   "correta": 0, "explicacao": "Está no material."}
        blocos = [
            bloco("cena_narrada", {"personagem": mascote, "visuais": [
                {"frase": 0, "tipo": "titulo", "texto": titulo}, {"frase": 1, "tipo": "cartao", "texto": "Vamos lá"}]},
                f"@{mascote}: Olá! Hoje vamos falar de {titulo}.\n@narrador: Preste atenção nos pontos principais.",
                "Abertura"),
            bloco("flashcards", {"cartoes": [{"frente": "Termo", "verso": "Definição"}, {"frente": "Outro", "verso": "Explicação"}]}),
            bloco("caca_erro", {"instrucao": "Ache o erro.", "trechos": [
                {"texto": "Frase certa.", "erro": False}, {"texto": "Frase errada.", "erro": True, "explicacao": "Contradiz o material."}]}),
            bloco("quiz_fixacao", {"questoes": [questao, {**questao, "correta": 1, "alternativas": ["X", "A certa", "Y"]}]}),
        ]
        n_prova = ctx.get("n_prova") or 2
        questoes = [
            {**questao, "enunciado": f"Questão de prova {i + 1} sobre {titulo}", "dificuldade": "media", "uso": "prova",
             "paginas_origem": p}
            for i in range(n_prova)
        ] + [{**questao, "dificuldade": "facil", "uso": "fixacao", "paginas_origem": p}]
        return {"blocos": blocos, "questoes": questoes}
