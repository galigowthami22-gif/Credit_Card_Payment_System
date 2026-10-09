from unittest.mock import Mock, patch

import jwt
from django.conf import settings
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cards.models import Card


class CardPaymentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='payment-user',
            password='test-password',
        )
        self.card = Card.objects.create(
            user=self.user,
            card_holder_name='Test User',
            masked_card_number='**** **** **** 4242',
            last_four_digits='4242',
            expiry_date='12/30',
        )
        self.client.force_login(self.user)

    @patch('cards.views.httpx.post')
    def test_payment_sends_short_lived_card_bound_token_to_fastapi(self, post_payment):
        post_payment.return_value = Mock(
            is_error=False,
            json=Mock(return_value={
                'transaction_id': 'TXN-TEST-123',
                'status': 'SUCCESS',
            }),
        )

        response = self.client.post(
            reverse('make_payment', args=[self.card.payment_reference]),
            {'amount': '25.50'},
        )

        self.assertRedirects(
            response,
            reverse('transaction-history-page'),
            fetch_redirect_response=False,
        )
        post_payment.assert_called_once()
        request = post_payment.call_args.kwargs
        self.assertEqual(
            request['json'],
            {
                'payment_reference': str(self.card.payment_reference),
                'amount': '25.50',
            },
        )

        authorization = request['headers']['Authorization']
        self.assertTrue(authorization.startswith('Bearer '))
        token = authorization.removeprefix('Bearer ')
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        self.assertEqual(payload['user_id'], self.user.pk)
        self.assertEqual(payload['scope'], 'payment')
        self.assertEqual(payload['payment_reference'], str(self.card.payment_reference))
        self.assertEqual(payload['card_last_four'], self.card.last_four_digits)

    @patch('cards.views.httpx.post')
    def test_invalid_amount_does_not_call_payment_service(self, post_payment):
        response = self.client.post(
            reverse('make_payment', args=[self.card.payment_reference]),
            {'amount': 'NaN'},
        )

        self.assertRedirects(
            response,
            reverse('card_list'),
            fetch_redirect_response=False,
        )
        post_payment.assert_not_called()


class CardManagementTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='card-owner', password='test-password')
        self.other_user = User.objects.create_user(username='other-owner', password='test-password')
        self.client.force_login(self.user)

    def test_add_card_stores_only_masked_number_and_no_cvv(self):
        response = self.client.post(
            reverse('add_card'),
            {
                'card_holder_name': 'Card Owner',
                'card_number': '4242 4242 4242 4242',
                'expiry_date': '12/99',
                'cvv': '123',
            },
        )

        self.assertRedirects(response, reverse('card_list'), fetch_redirect_response=False)
        card = Card.objects.get(user=self.user)
        self.assertEqual(card.masked_card_number, '**** **** **** 4242')
        self.assertEqual(card.last_four_digits, '4242')
        self.assertNotIn('card_number', {field.name for field in Card._meta.fields})
        self.assertNotIn('cvv', {field.name for field in Card._meta.fields})
        self.assertNotIn('4242424242424242', repr(card))

    def test_invalid_card_number_is_not_saved(self):
        self.client.post(
            reverse('add_card'),
            {
                'card_holder_name': 'Card Owner',
                'card_number': '4242424242424241',
                'expiry_date': '12/99',
            },
        )

        self.assertFalse(Card.objects.exists())

    def test_user_cannot_access_another_users_card(self):
        card = Card.objects.create(
            user=self.other_user,
            card_holder_name='Other Owner',
            masked_card_number='**** **** **** 4242',
            last_four_digits='4242',
            expiry_date='12/99',
        )

        response = self.client.get(reverse('edit_card', args=[card.pk]))

        self.assertEqual(response.status_code, 404)

    @patch('cards.views.httpx.post')
    def test_user_cannot_pay_with_another_users_payment_reference(self, post_payment):
        other_card = Card.objects.create(
            user=self.other_user,
            card_holder_name='Other Owner',
            masked_card_number='**** **** **** 4242',
            last_four_digits='4242',
            expiry_date='12/99',
        )

        response = self.client.post(
            reverse('make_payment', args=[other_card.payment_reference]),
            {'amount': '25.50'},
        )

        self.assertRedirects(response, reverse('card_list'), fetch_redirect_response=False)
        post_payment.assert_not_called()

    def test_card_delete_requires_post(self):
        card = Card.objects.create(
            user=self.user,
            card_holder_name='Card Owner',
            masked_card_number='**** **** **** 4242',
            last_four_digits='4242',
            expiry_date='12/99',
        )

        response = self.client.get(reverse('delete_card', args=[card.pk]))

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Card.objects.filter(pk=card.pk).exists())
