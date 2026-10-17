from decimal import Decimal
from typing import Optional, Dict, Any


def get_currency_symbol(currency_code: str) -> str:
    symbols = {
        "GBP": "£",
        "USD": "$",
        "EUR": "€",
    }
    return symbols.get((currency_code or "GBP").upper(), "£")


def format_pricing_display(
    pricing_model: str,
    price: Optional[Decimal],
    currency: str = "GBP",
    unit: Optional[str] = None,
    additional_fees: Optional[Dict[str, Any]] = None,
    inclusions: Optional[str] = None,
    exclusions: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Implements Section 9.4 Pricing display rules:
    - Fixed price: advertised price and inclusions.
    - From-price: display 'From £X' and explain variables.
    - Hourly/daily/per-unit: show amount and unit (e.g. '£40.00 / hour').
    - Package: package inclusions/exclusions.
    - Quote required: never display a misleading £0 price; display 'Request a Quote'.
    - Explains whether materials, travel, call-out, and emergency fees are included.
    """
    symbol = get_currency_symbol(currency)
    model = (pricing_model or "").lower().strip()
    formatted_amount = f"{symbol}{price:,.2f}" if price is not None and price > 0 else None

    display_label = ""
    pricing_note = ""

    if model == "fixed":
        display_label = formatted_amount if formatted_amount else f"{symbol}0.00"
        pricing_note = "Fixed price for the described scope of work."
    elif model == "from-price":
        display_label = f"From {formatted_amount}" if formatted_amount else "From price on request"
        pricing_note = "Starting price. Final cost depends on specific requirements, materials, or complexity."
    elif model in ["hourly", "daily", "per-unit"]:
        unit_str = unit or ("hour" if model == "hourly" else ("day" if model == "daily" else "unit"))
        display_label = f"{formatted_amount} / {unit_str}" if formatted_amount else f"Rate per {unit_str}"
        pricing_note = f"Charged per {unit_str}."
    elif model == "package":
        display_label = formatted_amount if formatted_amount else "Package Price"
        pricing_note = "Comprehensive package price including defined deliverables."
    elif model == "quote_required" or model == "quote":
        # Rule 9.4: Quote required: do not display a misleading £0 price; provide Request a Quote.
        display_label = "Request a Quote"
        pricing_note = "Custom quote tailored to your specific project needs."
    else:
        display_label = formatted_amount or "Contact for Price"
        pricing_note = "Pricing subject to confirmation."

    # Parse additional fees breakdown (materials, travel, call-out, emergency surcharge)
    fees_summary = {}
    if additional_fees and isinstance(additional_fees, dict):
        fees_summary = {
            "call_out_fee": additional_fees.get("call_out_fee"),
            "travel_fee": additional_fees.get("travel_fee"),
            "emergency_surcharge": additional_fees.get("emergency_surcharge"),
            "materials_included": additional_fees.get("materials_included", False),
            "materials_note": additional_fees.get("materials_note"),
            "minimum_charge": additional_fees.get("minimum_charge"),
        }

    return {
        "pricing_model": pricing_model,
        "raw_price": float(price) if price is not None else None,
        "currency": currency,
        "currency_symbol": symbol,
        "unit": unit,
        "display_label": display_label,
        "pricing_note": pricing_note,
        "additional_fees": fees_summary,
        "inclusions": inclusions,
        "exclusions": exclusions,
    }
