from django import forms
from django.contrib.auth import authenticate, password_validation
from django.core.cache import cache
from django.conf import settings

from .models import Usuario, ip_do_request


class LoginForm(forms.Form):
    email = forms.EmailField(label="E-mail")
    senha = forms.CharField(label="Senha", widget=forms.PasswordInput)

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.usuario = None
        super().__init__(*args, **kwargs)

    def _chave_rate(self, email):
        return f"login-falhas:{ip_do_request(self.request)}:{email}"

    def clean(self):
        dados = super().clean()
        email = (dados.get("email") or "").lower()
        senha = dados.get("senha")
        if not email or not senha:
            return dados
        limite, janela = settings.LOGIN_RATE_LIMIT
        chave = self._chave_rate(email)
        falhas = cache.get(chave, 0)
        if falhas >= limite:
            raise forms.ValidationError(
                "Muitas tentativas de login. Aguarde alguns minutos e tente de novo."
            )
        self.usuario = authenticate(self.request, email=email, password=senha)
        if self.usuario is None:
            cache.set(chave, falhas + 1, janela)
            raise forms.ValidationError("E-mail ou senha incorretos.")
        cache.delete(chave)
        return dados


class CadastroForm(forms.ModelForm):
    senha1 = forms.CharField(label="Senha", widget=forms.PasswordInput)
    senha2 = forms.CharField(label="Confirme a senha", widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ["nome", "email"]

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email=email).exists():
            raise forms.ValidationError("Já existe uma conta com este e-mail.")
        return email

    def clean(self):
        dados = super().clean()
        s1, s2 = dados.get("senha1"), dados.get("senha2")
        if s1 and s2 and s1 != s2:
            self.add_error("senha2", "As senhas não conferem.")
        if s1:
            usuario_tmp = Usuario(nome=dados.get("nome", ""), email=dados.get("email", ""))
            try:
                password_validation.validate_password(s1, usuario_tmp)
            except forms.ValidationError as erro:
                self.add_error("senha1", erro)
        return dados

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["senha1"])
        usuario.papel = Usuario.Papel.ALUNO
        if commit:
            usuario.save()
        return usuario
