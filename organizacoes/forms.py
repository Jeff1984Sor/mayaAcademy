import re

from django import forms

from core.models import Organizacao
from cursos.models import Curso

from .models import LicencaOrganizacao


class OrganizacaoForm(forms.ModelForm):
    class Meta:
        model = Organizacao
        fields = ["nome", "cnpj", "logo", "contato_nome", "contato_email", "contato_telefone", "ranking_ativo", "ativa"]


class LicencaForm(forms.ModelForm):
    class Meta:
        model = LicencaOrganizacao
        fields = ["curso", "vagas", "validade"]
        widgets = {"validade": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["curso"].queryset = Curso.objects.exclude(status=Curso.Status.ARQUIVADO)
        self.fields["vagas"].min_value = 1

    def clean_vagas(self):
        vagas = self.cleaned_data["vagas"]
        if self.instance.pk and vagas < self.instance.vagas_usadas:
            raise forms.ValidationError(f"Já há {self.instance.vagas_usadas} vagas usadas; não dá para reduzir abaixo disso.")
        if vagas < 1:
            raise forms.ValidationError("Informe pelo menos 1 vaga.")
        return vagas


class ConvitesForm(forms.Form):
    licenca = forms.ModelChoiceField(queryset=LicencaOrganizacao.objects.none(), label="Curso (licença)")
    emails = forms.CharField(
        label="E-mails", widget=forms.Textarea(attrs={"rows": 5, "placeholder": "um@empresa.com\noutro@empresa.com"}),
        help_text="Um por linha (ou separados por vírgula). Cada convite consome uma vaga só quando é aceito.",
    )

    def __init__(self, *args, organizacao=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["licenca"].queryset = LicencaOrganizacao.objects.filter(organizacao=organizacao).select_related("curso")
        self.fields["licenca"].label_from_instance = lambda lic: f"{lic.curso.titulo} — {lic.vagas_livres} vaga(s) livre(s), até {lic.validade:%d/%m/%Y}"

    def clean_emails(self):
        emails = [e.strip().lower() for e in re.split(r"[\s,;]+", self.cleaned_data["emails"]) if e.strip()]
        invalidos = [e for e in emails if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", e)]
        if invalidos:
            raise forms.ValidationError(f"E-mail(s) inválido(s): {', '.join(invalidos[:5])}")
        if not emails:
            raise forms.ValidationError("Informe pelo menos um e-mail.")
        return emails


class GestorForm(forms.Form):
    email = forms.EmailField(label="E-mail do gestor", help_text="A pessoa precisa ter conta na plataforma.")
