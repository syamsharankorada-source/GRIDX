from decimal import Decimal, ROUND_HALF_UP
from .models import ServiceCategory, PricingRule

def calculate_itemized_estimate(category: ServiceCategory, distance_km: float = 3.5, is_emergency: bool = True) -> dict:
    rule, _ = PricingRule.objects.get_or_create(category=category)
    dist_dec = Decimal(str(max(0.5, float(distance_km)))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    base = rule.base_charge
    distance_cost = (dist_dec * rule.per_km_charge).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    surcharge = rule.emergency_surcharge if is_emergency else Decimal('0.00')
    subtotal = base + distance_cost + surcharge
    platform_fee = (subtotal * (rule.platform_fee_pct / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    tax = ((subtotal + platform_fee) * (rule.tax_pct / Decimal('100.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total = (subtotal + platform_fee + tax).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return {
        "is_estimate": True,
        "category_name": category.name,
        "distance_km": str(dist_dec),
        "base_charge": str(base),
        "distance_charge": str(distance_cost),
        "emergency_surcharge": str(surcharge),
        "platform_fee": str(platform_fee),
        "tax": str(tax),
        "estimated_total": str(total),
        "min_range": str((total * Decimal('0.90')).quantize(Decimal('1.00'))),
        "max_range": str((total * Decimal('1.15')).quantize(Decimal('1.00'))),
    }
