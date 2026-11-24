"""Config inicial (válida) de cada tipo de bloco — usada ao criar um bloco no Estúdio."""

EXEMPLOS = {
    "cena_narrada": {
        "roteiro": "@narrador: Comece aqui a narração. Cada frase pode disparar um visual.",
        "config": {"fundo": "palco", "visuais": [{"frase": 0, "tipo": "titulo", "texto": "Título da cena"}]},
    },
    "dialogo": {
        "roteiro": "@narrador: Olá! Sobre o que vamos conversar hoje?\n@mascote: Sobre um assunto muito importante.",
        "config": {"fundo": "estudio"},
    },
    "chat_simulado": {
        "roteiro": "",
        "config": {
            "nome_usuario": "Você", "nome_ia": "Assistente de IA",
            "mensagens": [
                {"de": "usuario", "texto": "Pergunta do usuário"},
                {"de": "ia", "texto": "Resposta da IA", "nota": "Comentário didático sobre a resposta", "nota_tipo": "info"},
            ],
        },
    },
    "antes_depois": {
        "roteiro": "",
        "config": {"rotulo_antes": "Antes", "rotulo_depois": "Depois", "antes": "Versão fraca", "depois": "Versão melhorada", "comentario": "O que mudou e por quê."},
    },
    "arrastar_soltar": {
        "roteiro": "",
        "config": {
            "instrucao": "Classifique cada item.",
            "categorias": [{"id": "a", "nome": "Categoria A"}, {"id": "b", "nome": "Categoria B"}],
            "itens": [{"texto": "Item 1", "categoria": "a"}, {"texto": "Item 2", "categoria": "b"}],
        },
    },
    "montador": {
        "roteiro": "",
        "config": {
            "instrucao": "Monte peça por peça.",
            "pecas": [
                {"rotulo": "Parte 1", "texto": "Texto da parte 1", "peso": 50},
                {"rotulo": "Parte 2", "texto": "Texto da parte 2", "peso": 50},
                {"rotulo": "Distrator", "texto": "Algo que atrapalha", "distrator": True, "feedback": "Por que atrapalha"},
            ],
            "mensagem_final": "Montagem completa!",
        },
    },
    "caca_erro": {
        "roteiro": "",
        "config": {
            "instrucao": "Encontre os erros no texto.",
            "trechos": [
                {"texto": "Trecho correto."},
                {"texto": "Trecho com erro.", "erro": True, "explicacao": "Por que está errado."},
            ],
        },
    },
    "cenario_ramificado": {
        "roteiro": "",
        "config": {
            "inicio": "n1",
            "nos": [
                {"id": "n1", "texto": "Descreva a situação.", "escolhas": [
                    {"texto": "Opção boa", "tipo": "bom", "consequencia": "O que acontece de bom."},
                    {"texto": "Opção ruim", "tipo": "ruim", "consequencia": "O que dá errado.", "vai_para": "n2"},
                ]},
                {"id": "n2", "texto": "Desdobramento da escolha ruim."},
            ],
        },
    },
    "flashcards": {
        "roteiro": "",
        "config": {"cartoes": [{"frente": "Termo", "verso": "Definição"}, {"frente": "Termo 2", "verso": "Definição 2"}]},
    },
    "quiz_fixacao": {
        "roteiro": "",
        "config": {"questoes": [
            {"enunciado": "Pergunta 1?", "alternativas": ["Certa", "Errada"], "correta": 0, "explicacao": "Explicação."},
            {"enunciado": "Pergunta 2?", "alternativas": ["Errada", "Certa"], "correta": 1, "explicacao": "Explicação."},
        ]},
    },
    "missao": {
        "roteiro": "",
        "config": {
            "titulo": "Nome da missão", "contexto": "Descreva o caso prático.",
            "passos": [
                {"enunciado": "Primeiro passo?", "alternativas": ["Certo", "Errado"], "correta": 0, "explicacao": "Explicação."},
                {"enunciado": "Segundo passo?", "alternativas": ["Errado", "Certo"], "correta": 1, "explicacao": "Explicação."},
            ],
            "recompensa": "Mensagem de conclusão.",
        },
    },
    "texto_apoio": {"roteiro": "", "texto_tela": "Texto curto de apoio.", "config": {"destaque": "Ponto principal."}},
}
