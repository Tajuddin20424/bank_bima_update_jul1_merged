from django.test import SimpleTestCase, TestCase

from .views import _allocate_amount

# Create your tests here.


class PharmacyAmountAllocationTests(SimpleTestCase):
    def test_allocation_preserves_transaction_total(self):
        allocations = _allocate_amount(300, [170, 480, 750])

        self.assertEqual(sum(allocations), 300.0)
        self.assertEqual(allocations, [36.42, 102.85, 160.73])

    def test_allocation_handles_zero_weights(self):
        allocations = _allocate_amount(890, [0, 0, 0])

        self.assertEqual(sum(allocations), 890.0)
