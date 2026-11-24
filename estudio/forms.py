import json

from django import forms

from cursos import blocos as registro
from cursos.models import Aula, BlocoAula, Curso, Modulo, Personagem, Questao


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = [
            "titulo", "slug", "subtitulo", "descricao", "capa", "carga_horaria", "nivel", "categoria",
            "modo_acesso", "preco", "nota_minima", "tentativas", "questoes_sorteadas", "aula_amostra",
            "cor_primaria", "cor_secundaria",
        ]
        widgets = {
            "descricao": forms.Textarea(attrs={"rows": 5}),
            "cor_primaria": forms.TextInput(attrs={"type": "color"}),
            "cor_secundaria": forms.TextInput(attrs={"type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False
        if self.instance.pk:
            self.fields["aula_amostra"].queryset = Aula.objects.filter(modulo__curso=self.instance).select_related("modulo")
        else:
            self.fields.pop("aula_amostra")


class PersonagemForm(forms.ModelForm):
    class Meta:
        model = Personagem
        fields = ["slug", "nome", "papel", "voz_nome", "voz_velocidade", "voz_tom", "avatar_padrao", "avatar", "cor"]
        widgets = {"cor": forms.TextInput(attrs={"type": "color"})}
        help_texts = {"avatar_padrao": "maya (hexágono), coruja ou robo"}


class ModuloForm(forms.ModelForm):
    class Meta:
        model = Modulo
        fields = ["titulo"]


class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        fields = ["titulo", "objetivo", "duracao_min", "xp", "material", "precisa_revisao"]
        widgets = {"objetivo": forms.Textarea(attrs={"rows": 2})}


class BlocoForm(forms.ModelForm):
    config = forms.CharField(widget=forms.Textarea(attrs={"rows": 12, "class": "font-mono text-sm"}), required=False)
    paginas_origem = forms.CharField(required=False, help_text="Páginas do PDF de origem, separadas por vírgula")

    class Meta:
        model = BlocoAula
        fields = ["tipo", "titulo", "roteiro", "texto_tela", "config", "paginas_origem", "alem_do_pdf"]
        widgets = {
            "roteiro": forms.Textarea(attrs={"rows": 8, "class": "font-mono text-sm"}),
            "texto_tela": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.initial["config"] = json.dumps(self.instance.config, ensure_ascii=False, indent=2)
            self.initial["paginas_origem"] = ", ".join(str(p) for p in self.instance.paginas_origem)

    def clean_config(self):
        bruto = self.cleaned_data.get("config") or "{}"
        try:
            valor = json.loads(bruto)
        except json.JSONDecodeError as erro:
            raise forms.ValidationError(f"JSON inválido (linha {erro.lineno}, coluna {erro.colno}): {erro.msg}") from erro
        return valor

    def clean_paginas_origem(self):
        bruto = self.cleaned_data.get("paginas_origem") or ""
        try:
            return [int(p) for p in bruto.replace(";", ",").split(",") if p.strip()]
        except ValueError as erro:
            raise forms.ValidationError("Use só números separados por vírgula.") from erro

    def clean(self):
        dados = super().clean()
        if "config" in dados and dados.get("tipo"):
            erros = registro.validar_bloco(dados["tipo"], dados["config"], dados.get("roteiro") or "")
            if erros:
                self.add_error("config", erros)
        return dados


class QuestaoForm(forms.ModelForm):
    alternativas = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), help_text="Uma alternativa por linha")

    class Meta:
        model = Questao
        fields = ["modulo", "enunciado", "alternativas", "correta", "explicacao", "dificuldade", "uso", "ativa"]
        widgets = {"enunciado": forms.Textarea(attrs={"rows": 2}), "explicacao": forms.Textarea(attrs={"rows": 2})}
        help_texts = {"correta": "Número da alternativa correta, começando em 0"}

    def __init__(self, *args, curso=None, **kwargs):
        super().__init__(*args, **kwargs)
        if curso is not None:
            self.fields["modulo"].queryset = curso.modulos.all()
        if self.instance.pk:
            self.initial["alternativas"] = "\n".join(self.instance.alternativas)

    def clean_alternativas(self):
        alts = [a.strip() for a in self.cleaned_data["alternativas"].splitlines() if a.strip()]
        if len(alts) < 2:
            raise forms.ValidationError("Informe pelo menos 2 alternativas.")
        return alts


class ImportarForm(forms.Form):
    arquivo = forms.FileField(help_text="Roteiro .yaml, .yml ou .json")
    curso_destino = forms.ModelChoiceField(
        queryset=Curso.objects.all(), required=False,
        help_text="Deixe vazio para criar um curso novo. Escolha um curso para importar só módulos/aulas nele.",
    )

    def clean_arquivo(self):
        f = self.cleaned_data["arquivo"]
        if not f.name.lower().endswith((".yaml", ".yml", ".json")):
            raise forms.ValidationError("Envie um arquivo .yaml, .yml ou .json.")
        if f.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Arquivo maior que 5 MB.")
        return f
