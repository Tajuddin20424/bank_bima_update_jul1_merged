from django.test import SimpleTestCase
from django.urls import reverse

class BankBimaPartyPaymentTests(SimpleTestCase):
    def test_party_payment_list_route_exists(self):
        self.assertEqual(reverse("bank_bima_party_payment_list"), "/bank-bima/party-payment/")


# Add Bank Bima-specific tests here as the app's workflows are expanded.
