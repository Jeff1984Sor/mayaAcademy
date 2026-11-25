from django import forms
from django.conf import settings

from .models import Geracao


class VariosArquivos(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoVariosPDFs(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", VariosArquivos(attrs={"accept": "application/pdf,.pdf"}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        arquivos = data if isinstance(data, (list, tuple)) else [data]
        arquivos = [f for f in arquivos if f]
        if not arquivos:
            raise forms.ValidationError("Envie pelo menos um PDF.")
        return [super(CampoVariosPDFs, self).clean(f, initial) for f in arquivos]


def contar_paginas(arquivo):
    import pymupdf as fitz

    arquivo.seek(0)
    try:
        with fitz.open(stream=arquivo.read(), filetype="pdf") as doc:
            if doc.needs_pass:
                raise forms.ValidationError(f"{arquivo.name}: o PDF tem senha; envie a versão sem senha.")
            return len(doc)
    except (RuntimeError, ValueError) as erro:
        raise forms.ValidationError(f"{arquivo.name}: não é um PDF válido.") from erro
    finally:
        arquivo.seek(0)


class NovaGeracaoForm(forms.ModelForm):
    pdfs = CampoVariosPDFs(label="PDF(s) do material", help_text="Um ou mais PDFs (apostila, manual, e-book). São lidos na ordem em que aparecem.")
    declaracao = forms.BooleanField(
        label="Declaro que tenho direito de uso deste material para criar cursos",
        error_messages={"required": "Para continuar, confirme que tem direito de uso do material."},
    )

    class Meta:
        model = Geracao
        fields = ["titulo", "publico", "nivel", "tom", "duracao_horas", "n_modulos", "narrador_nome", "mascote_nome", "idioma"]
        help_texts = {
            "titulo": "Só para você reconhecer esta geração (a IA propõe o título do curso).",
            "publico": "Ex.: instrutores iniciantes de Pilates; equipe de atendimento.",
            "idioma": "Padrão pt-BR.",
        }

    def clean_pdfs(self):
        arquivos = self.cleaned_data["pdfs"]
        total = 0
        for f in arquivos:
            if not f.name.lower().endswith(".pdf"):
                raise forms.ValidationError(f"{f.name}: envie só arquivos .pdf.")
            total += contar_paginas(f)
        limite = settings.PDF_LIMITE_PAGINAS
        if total > limite:
            raise forms.ValidationError(f"Os PDFs somam {total} páginas; o limite é {limite}. Divida o material.")
        self.total_paginas = total
        return arquivos
