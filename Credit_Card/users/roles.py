from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

ROLE_ADMIN = "admin"
ROLE_MANAGER = "manager"
ROLE_USER = "user"

ROLE_GROUPS = (ROLE_MANAGER, ROLE_USER)
MANAGER_PERMISSIONS = (
    ("auth", "user", ("add", "change", "delete", "view")),
    ("cards", "card", ("add", "change", "delete", "view")),
    ("transactions", "transaction", ("view",)),
)


def get_role(user):
    if user.is_superuser:
        return ROLE_ADMIN
    if user.groups.filter(name=ROLE_MANAGER).exists():
        return ROLE_MANAGER
    if user.is_staff:
        return ROLE_ADMIN
    return ROLE_USER


def assign_role(user, role):
    if role not in ROLE_GROUPS:
        raise ValueError(f"Role must be one of {ROLE_GROUPS}.")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.set([group])
    user.is_staff = role == ROLE_MANAGER
    user.save(update_fields=("is_staff",))


@receiver(post_save, sender=get_user_model(), dispatch_uid="users.assign_default_role")
def assign_default_role(sender, instance, created, **kwargs):
    if created and not instance.is_staff and not instance.is_superuser:
        group, _ = Group.objects.get_or_create(name=ROLE_USER)
        instance.groups.add(group)


@receiver(post_migrate, dispatch_uid="users.configure_role_groups")
def configure_role_groups(sender, **kwargs):
    for role in ROLE_GROUPS:
        Group.objects.get_or_create(name=role)

    manager_group = Group.objects.get(name=ROLE_MANAGER)
    permissions = []
    for app_label, model, actions in MANAGER_PERMISSIONS:
        content_type, _ = ContentType.objects.get_or_create(
            app_label=app_label,
            model=model,
        )
        for action in actions:
            permission, _ = Permission.objects.get_or_create(
                content_type=content_type,
                codename=f"{action}_{model}",
                defaults={"name": f"Can {action} {model}"},
            )
            permissions.append(permission)
    manager_group.permissions.set(permissions)
