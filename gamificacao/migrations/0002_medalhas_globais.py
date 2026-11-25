from django.db import migrations

MEDALHAS = [
    ("primeiro-certificado", "Primeiro certificado", "Conquistou o primeiro certificado na MayaAcademy.", "🎓", "primeiro_certificado", 0, 100),
    ("nota-100", "Nota 100", "Acertou todas as questões de uma prova final.", "💯", "nota_100", 0, 100),
    ("maratonista", "Maratonista", "Concluiu um curso em até 7 dias.", "🏃", "maratonista", 7, 80),
    ("mil-xp", "Mil de XP", "Somou 1.000 pontos de experiência.", "⭐", "xp_total", 1000, 50),
]


def criar(apps, schema_editor):
    Medalha = apps.get_model("gamificacao", "Medalha")
    for slug, nome, descricao, icone, criterio, parametro, bonus in MEDALHAS:
        Medalha.objects.get_or_create(slug=slug, defaults={
            "nome": nome, "descricao": descricao, "icone": icone, "criterio": criterio,
            "parametro": parametro, "xp_bonus": bonus,
        })


def remover(apps, schema_editor):
    apps.get_model("gamificacao", "Medalha").objects.filter(slug__in=[m[0] for m in MEDALHAS]).delete()


class Migration(migrations.Migration):
    dependencies = [("gamificacao", "0001_initial")]
    operations = [migrations.RunPython(criar, remover)]
