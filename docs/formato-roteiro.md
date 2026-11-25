# Formato de roteiro da MayaAcademy (`mayaacademy/v1`)

Um arquivo **YAML** (ou JSON, com a mesma estrutura) descreve um curso inteiro, ou só módulos e aulas para acrescentar a um curso que já existe. Ele é usado em três lugares:

- **Estúdio › Importar roteiro**: valida, mostra os erros com o número da linha, mostra a prévia e cria o curso como **rascunho**.
- **Estúdio › curso › Exportar roteiro**: gera o mesmo formato, para backup ou para reaproveitar um curso.
- No servidor: `python manage.py importar_roteiro arquivo.yaml` (use `--validar` para só conferir, ou `--curso <slug>` para acrescentar módulos a um curso existente).

O exemplo real completo está em [`conteudo/ia-com-sabedoria-piloto.yaml`](../conteudo/ia-com-sabedoria-piloto.yaml), que é a aula-piloto "Limites e alucinações".

---

## 1. Estrutura geral

```yaml
formato: mayaacademy/v1      # opcional, mas recomendado

curso:                       # omita para importar só módulos num curso existente
  titulo: Nome do curso      # obrigatório
  slug: nome-do-curso        # opcional (gerado do título); precisa ser único
  subtitulo: ...
  descricao: |
    Texto longo da página de venda.
  carga_horaria: 4           # horas (vai no certificado)
  nivel: iniciante           # iniciante | intermediario | avancado
  categoria: ...
  modo_acesso: gratuito      # gratuito | pago | convite
  preco: 0
  nota_minima: 70            # % para aprovar na prova final
  tentativas: 3
  questoes_sorteadas: 10     # a prova sorteia N do banco; para publicar precisa de N × 1,5 questões de prova
  cor_primaria: "#1E2D6B"    # padrão MayaCorp (Navy)
  cor_secundaria: "#F5A623"  # padrão MayaCorp (Amber)

personagens:                 # quem fala nos roteiros
  - slug: narrador           # usado no roteiro como @narrador:
    nome: Narrador
    papel: narrador          # narrador | mascote
    voz: pt-BR-Neural2-B     # voz do TTS
    velocidade: 1.0          # 0.25 a 4.0
    tom: 0.0                 # -20 a 20
    avatar: coruja           # maya (hexágono) | coruja | robo
    cor: "#1A8F5E"

modulos:
  - titulo: Nome do módulo
    aulas:
      - titulo: Nome da aula
        objetivo: O que o aluno consegue fazer ao final.
        duracao_min: 15
        xp: 150
        blocos: [ ... ]      # ver seção 3

questoes:                    # banco de questões (fixação e prova final)
  - modulo: 1                # número do módulo (1, 2, ...) — opcional
    enunciado: ...
    alternativas: [A, B, C, D]
    correta: 1               # ÍNDICE da correta, começando em 0
    explicacao: ...
    dificuldade: media       # facil | media | dificil
    uso: prova               # fixacao | prova | ambos
    paginas_origem: [12, 13] # opcional (cursos gerados de PDF)
```

## 2. Regras que o validador confere

- **Toda aula tem no mínimo 4 blocos, pelo menos 2 interativos e nunca só texto.** Interativos: `antes_depois`, `arrastar_soltar`, `montador`, `caca_erro`, `cenario_ramificado`, `flashcards`, `quiz_fixacao`, `missao`.
- A `config` de cada bloco segue o schema do tipo (seção 3). Campo desconhecido também é erro, porque costuma ser erro de digitação.
- Todo `@personagem` usado num roteiro precisa estar em `personagens`.
- `cena_narrada` e `dialogo` exigem roteiro.
- Para publicar, também é preciso: todos os áudios gerados, e N × 1,5 questões de prova ativas. Isso é conferido no checklist de publicação, não na importação.

## 3. Roteiro de narração

```text
@maya: Oi! Eu sou a Maya.
Esta linha continua a fala da Maya.
@narrador: Agora fala o narrador. [pausa 800ms] Depois de uma pausa.
Palavras entre asteriscos ganham *ênfase*.
```

- Uma fala por linha, no formato `@slug: texto`. Linhas sem `@` continuam o último personagem. Sem nenhum `@`, a fala é do `narrador`.
- A fala é dividida em **frases** em `.`, `!`, `?` e `…`. Cada frase recebe um número global, começando em 0 e seguindo a ordem de todo o roteiro. Esse número sincroniza animação e legenda.
  - Atenção: "Oi! Eu sou a Maya." são **duas** frases (0 e 1).
  - No Estúdio, o editor do bloco mostra a lista "Frases numeradas".
- `[pausa]` = 500 ms; `[pausa 800ms]` = pausa definida.
- A legenda e a transcrição são geradas do roteiro (acessibilidade obrigatória).

Campos comuns a todos os blocos:

```yaml
- tipo: caca_erro            # obrigatório
  titulo: Título do bloco
  roteiro: |                 # narração (opcional nos interativos)
    @narrador: ...
  texto_tela: Texto curto acima da atividade (aceita **negrito**, *itálico*, listas "- ").
  config: { ... }            # específico do tipo
  paginas_origem: [3, 4]     # opcional (gerador por PDF)
  alem_do_pdf: true          # opcional: selo "⚠ conteúdo além do PDF"
```

### Tipos de bloco e sua `config`

| Tipo | `config` |
|---|---|
| `cena_narrada` | `personagem` (slug), `fundo` (`palco`/`quadro`/`escritorio`/`espaco`), `lottie` (URL opcional), **`visuais`**: lista de `{frase, tipo, texto, itens, icone, estado}`. `tipo` do visual: `titulo`, `cartao`, `lista`, `icone`, `alerta`, `citacao`, `numero`. `estado` muda a expressão do personagem: `neutro`, `falando`, `pensando`, `comemorando`, `alerta`. |
| `dialogo` | `titulo`, `fundo` (`estudio`/`palco`). O conteúdo é o roteiro com dois ou mais personagens. |
| `chat_simulado` | `titulo`, `nome_usuario`, `nome_ia`, **`mensagens`** (mín. 2): `{de: usuario/ia/sistema, texto, nota, nota_tipo: alerta/ok/info}` |
| `antes_depois` | **`rotulo_antes`**, **`rotulo_depois`**, **`antes`**, **`depois`**, `comentario` (aparece depois de comparar) |
| `arrastar_soltar` | **`instrucao`**, **`categorias`** (2 a 4): `{id, nome}`, **`itens`**: `{texto, categoria (id), feedback}` |
| `montador` | **`instrucao`**, `objetivo`, **`pecas`**: `{rotulo, texto, peso 0–100, distrator: true/false, feedback}`, `mensagem_final`, `em_ordem` (true: as peças certas têm de ser tocadas na ordem em que aparecem na config; na tela elas aparecem embaralhadas) |
| `caca_erro` | **`instrucao`**, `contexto`, **`trechos`**: `{texto, erro: true/false, explicacao}`. Todo trecho com erro precisa de explicação. |
| `cenario_ramificado` | `titulo`, **`inicio`** (id), **`nos`**: `{id, texto, escolhas: [{texto, consequencia, tipo: bom/ruim/neutro, vai_para}]}`. Escolha sem `vai_para`, ou nó sem escolhas, é um final. |
| `flashcards` | **`cartoes`** (mín. 2): `{frente, verso}` |
| `quiz_fixacao` | **`questoes`** (2 a 4): `{enunciado, alternativas, correta, explicacao}` |
| `missao` | **`titulo`**, **`contexto`**, **`passos`** (mín. 2, mesmo formato das questões), `recompensa` |
| `texto_apoio` | `destaque`, `icone`. O texto vai em `texto_tela`. |

Em **negrito**: obrigatório.

## 4. Exemplo completo de uma aula

```yaml
formato: mayaacademy/v1
curso:
  titulo: Atendimento que encanta
  slug: atendimento-que-encanta
  carga_horaria: 2
  questoes_sorteadas: 2
personagens:
  - { slug: narrador, nome: Narrador, papel: narrador, voz: pt-BR-Neural2-B, avatar: coruja, cor: "#1A8F5E" }
  - { slug: maya, nome: Maya, papel: mascote, voz: pt-BR-Neural2-C, avatar: maya, cor: "#7C8FFF" }
modulos:
  - titulo: Primeiro contato
    aulas:
      - titulo: Os 3 primeiros minutos
        objetivo: Conduzir a abertura de um atendimento com empatia e clareza.
        duracao_min: 12
        xp: 120
        blocos:
          - tipo: cena_narrada
            titulo: Por que o começo importa
            roteiro: |
              @maya: Sabia que a primeira impressão de um atendimento se forma em segundos?
              @narrador: Nos três primeiros minutos o cliente decide se confia em você.
              Por isso, vamos treinar três atitudes: ouvir, confirmar e combinar o próximo passo.
            config:
              personagem: maya
              visuais:
                - { frase: 0, tipo: titulo, texto: "Os 3 primeiros minutos" }
                - { frase: 1, tipo: numero, texto: "3 min", itens: ["para conquistar a confiança"] }
                - { frase: 2, tipo: lista, texto: "Três atitudes", itens: [Ouvir, Confirmar, Combinar o próximo passo], estado: comemorando }

          - tipo: chat_simulado
            titulo: Um começo apressado
            config:
              nome_usuario: Cliente
              nome_ia: Atendente
              mensagens:
                - { de: usuario, texto: "Oi, meu pedido não chegou." }
                - { de: ia, texto: "Qual o número do pedido?", nota: "Pulou a empatia: o cliente ainda nem foi ouvido.", nota_tipo: alerta }

          - tipo: arrastar_soltar
            titulo: Bom ou ruim?
            config:
              instrucao: Classifique cada frase de abertura.
              categorias: [ { id: boa, nome: Boa abertura }, { id: ruim, nome: Evitar } ]
              itens:
                - { texto: "Entendo, vamos resolver isso juntos.", categoria: boa }
                - { texto: "Isso não é comigo.", categoria: ruim, feedback: "Transfere a responsabilidade sem ajudar." }
                - { texto: "Deixa eu confirmar se entendi: ...", categoria: boa }

          - tipo: quiz_fixacao
            titulo: Fixando
            config:
              questoes:
                - enunciado: Qual a primeira atitude ao receber uma reclamação?
                  alternativas: [Pedir documentos, Ouvir o cliente, Oferecer desconto]
                  correta: 1
                  explicacao: Ouvir primeiro mostra respeito e traz as informações de que você precisa.
                - enunciado: Para que serve confirmar o que entendeu?
                  alternativas: [Ganhar tempo, Evitar mal-entendidos]
                  correta: 1
                  explicacao: Repetir com suas palavras evita resolver o problema errado.
questoes:
  - { modulo: 1, enunciado: "O que fazer nos primeiros minutos?", alternativas: [Ouvir, Vender], correta: 0, explicacao: "Ouvir vem antes.", uso: prova }
  - { modulo: 1, enunciado: "Confirmar o entendimento evita...", alternativas: [Mal-entendidos, Vendas], correta: 0, explicacao: "Alinhamento.", uso: prova }
  - { modulo: 1, enunciado: "Combinar o próximo passo dá ao cliente...", alternativas: [Previsibilidade, Desconto], correta: 0, explicacao: "Ele sabe o que esperar.", uso: prova }
```

## 5. Pedindo um roteiro ao Claude

Cole este documento na conversa e peça, por exemplo:

> Gere um roteiro no formato `mayaacademy/v1` para um curso sobre **<tema>**, público **<público>**, tom **<leve/formal/técnico>**, com **<N>** módulos.
> Cada aula precisa ter de 4 a 7 blocos, pelo menos 2 interativos, narração conversada entre `@narrador` e `@maya`, e ao menos uma `cena_narrada` com visuais sincronizados por número de frase.
> Inclua `questoes` de prova suficientes (`questoes_sorteadas` × 1,5). Use só fatos que eu forneço; marque com `alem_do_pdf: true` o que você complementar.

Depois importe em **Estúdio › Importar roteiro**. Se houver erro, a tela mostra a linha exata: devolva os erros ao Claude e peça a correção.
