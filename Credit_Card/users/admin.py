from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms

from .roles import ROLE_ADMIN, ROLE_MANAGER, ROLE_USER, assign_role, get_role


class ManagedUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


class RoleUserCreationForm(ManagedUserCreationForm):
    role = forms.ChoiceField(
        choices=(
            (ROLE_USER, "User"),
            (ROLE_MANAGER, "Manager"),
            (ROLE_ADMIN, "Admin"),
        ),
    )

    def save(self, commit=True):
        user = super().save(commit=False)
        role = self.cleaned_data["role"]
        user.is_staff = role in (ROLE_MANAGER, ROLE_ADMIN)
        user.is_superuser = role == ROLE_ADMIN
        user._pending_role = role
        if commit:
            user.save()
            self.save_m2m()
        return user

    def save_m2m(self):
        super().save_m2m()
        role = getattr(self.instance, "_pending_role", self.cleaned_data["role"])
        if role == ROLE_ADMIN:
            self.instance.groups.clear()
        else:
            assign_role(self.instance, role)


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = ManagedUserCreationForm

    def get_form(self, request, obj=None, **kwargs):
        if obj is None and request.user.is_superuser:
            kwargs["form"] = RoleUserCreationForm
        return super().get_form(request, obj, **kwargs)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if get_role(request.user) == ROLE_MANAGER:
            queryset = queryset.filter(is_staff=False, is_superuser=False)
        return queryset

    def get_fieldsets(self, request, obj=None):
        if obj is None and request.user.is_superuser:
            return (
                (
                    None,
                    {
                        "classes": ("wide",),
                        "fields": (
                            "username",
                            "password1",
                            "password2",
                            "email",
                            "first_name",
                            "last_name",
                            "role",
                        ),
                    },
                ),
            )
        if get_role(request.user) != ROLE_MANAGER:
            return super().get_fieldsets(request, obj)

        if obj is None:
            return (
                (
                    None,
                    {
                        "classes": ("wide",),
                        "fields": (
                            "username",
                            "password1",
                            "password2",
                            "email",
                            "first_name",
                            "last_name",
                        ),
                    },
                ),
            )
        return (
            (None, {"fields": ("username", "password")}),
            ("Personal info", {"fields": ("first_name", "last_name", "email")}),
            ("Account", {"fields": ("is_active",)}),
        )
