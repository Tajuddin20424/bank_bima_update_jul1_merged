from decimal import Decimal, ROUND_DOWN


def allocate_amount(total, weights):
    """Split one transaction amount across detail rows, preserving the total."""
    target = Decimal(str(total or 0)).quantize(Decimal("0.01"))
    clean_weights = [max(Decimal(str(weight or 0)), Decimal("0")) for weight in weights]
    if not clean_weights:
        return []
    weight_total = sum(clean_weights, Decimal("0"))
    if weight_total == 0:
        clean_weights = [Decimal("1")] * len(clean_weights)
        weight_total = Decimal(len(clean_weights))

    allocations = []
    allocated = Decimal("0")
    for weight in clean_weights[:-1]:
        share = (target * weight / weight_total).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        allocations.append(share)
        allocated += share
    allocations.append(target - allocated)
    return [float(value) for value in allocations]
