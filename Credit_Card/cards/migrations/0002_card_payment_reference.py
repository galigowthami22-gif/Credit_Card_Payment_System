import uuid

from django.db import migrations, models


def populate_payment_references(apps, schema_editor):
    Card = apps.get_model("cards", "Card")
    database = schema_editor.connection.alias
    for card in Card.objects.using(database).filter(payment_reference__isnull=True).iterator():
        Card.objects.using(database).filter(pk=card.pk).update(
            payment_reference=uuid.uuid4()
        )


class Migration(migrations.Migration):

    dependencies = [
        ("cards", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="card",
            name="payment_reference",
            field=models.UUIDField(null=True, editable=False),
        ),
        migrations.RunPython(
            populate_payment_references,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="card",
            name="payment_reference",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
