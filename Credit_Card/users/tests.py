from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from users.roles import ROLE_ADMIN, ROLE_MANAGER, ROLE_USER, assign_role


class AuthenticationTests(TestCase):
    def test_registration_hashes_password_and_allows_authentication(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "new-user",
                "email": "new-user@example.com",
                "password": "Long-test-password-123!",
            },
        )

        self.assertRedirects(response, reverse("dashboard"), fetch_redirect_response=False)
        user = User.objects.get(username="new-user")
        self.assertNotEqual(user.password, "Long-test-password-123!")
        self.assertTrue(user.check_password("Long-test-password-123!"))
        self.assertEqual(authenticate(username="new-user", password="Long-test-password-123!"), user)
        self.assertTrue(user.groups.filter(name=ROLE_USER).exists())

    def test_login_rejects_invalid_credentials(self):
        User.objects.create_user(username="existing-user", password="correct-password")

        response = self.client.post(
            reverse("login"),
            {"username": "existing-user", "password": "incorrect-password"},
        )

        self.assertRedirects(response, reverse("login"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_access_token_endpoint_requires_a_session(self):
        response = self.client.get(reverse("api-token"))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)


class RoleBasedAccessTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="site-admin",
            email="admin@example.com",
            password="test-password",
        )
        self.manager = User.objects.create_user(username="manager", password="test-password")
        assign_role(self.manager, ROLE_MANAGER)
        self.regular_user = User.objects.create_user(
            username="regular-user",
            password="test-password",
        )

    def test_manager_receives_expected_model_permissions_only(self):
        self.assertTrue(self.manager.is_staff)
        self.assertTrue(self.manager.has_perm("auth.add_user"))
        self.assertTrue(self.manager.has_perm("auth.change_user"))
        self.assertTrue(self.manager.has_perm("cards.add_card"))
        self.assertTrue(self.manager.has_perm("cards.delete_card"))
        self.assertTrue(self.manager.has_perm("transactions.view_transaction"))
        self.assertFalse(self.manager.has_perm("transactions.change_transaction"))
        self.assertFalse(self.manager.has_perm("auth.change_group"))

    def test_regular_user_has_no_admin_permissions(self):
        self.assertFalse(self.regular_user.is_staff)
        self.assertFalse(self.regular_user.has_perm("auth.view_user"))
        self.assertFalse(self.regular_user.has_perm("cards.view_card"))

    def test_manager_can_open_admin_user_management(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("admin:auth_user_changelist"))

        self.assertEqual(response.status_code, 200)
        visible_usernames = {
            user.username for user in response.context["cl"].result_list
        }
        self.assertIn("regular-user", visible_usernames)
        self.assertNotIn("manager", visible_usernames)

    def test_manager_user_form_hides_privilege_assignment_fields(self):
        self.client.force_login(self.manager)

        response = self.client.get(reverse("admin:auth_user_add"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="is_staff"')
        self.assertNotContains(response, 'name="is_superuser"')
        self.assertNotContains(response, 'name="groups"')

    def test_regular_user_cannot_open_admin(self):
        self.client.force_login(self.regular_user)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 302)

    def test_only_superuser_sees_register_admin_link(self):
        self.client.force_login(self.admin)
        admin_response = self.client.get(reverse("dashboard"))
        self.assertContains(admin_response, reverse("admin:auth_user_add"))

        self.client.force_login(self.regular_user)
        user_response = self.client.get(reverse("dashboard"))
        self.assertNotContains(user_response, reverse("admin:auth_user_add"))

    def test_superuser_can_create_an_admin_from_the_protected_form(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse("admin:auth_user_add"),
            {
                "username": "new-site-admin",
                "password1": "Strong-admin-password-123!",
                "password2": "Strong-admin-password-123!",
                "email": "new-admin@example.com",
                "first_name": "New",
                "last_name": "Admin",
                "role": ROLE_ADMIN,
            },
        )

        self.assertEqual(response.status_code, 302)
        new_admin = User.objects.get(username="new-site-admin")
        self.assertTrue(new_admin.is_staff)
        self.assertTrue(new_admin.is_superuser)
        self.assertTrue(new_admin.check_password("Strong-admin-password-123!"))
