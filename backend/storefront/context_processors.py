def cart_summary(request):
    """Cart badge data for every template.

    Phase 1a reads the raw session map ({variant_id: qty}); phase 1b swaps
    this for orders.SessionCart once that exists.
    """
    cart = request.session.get("cart", {})
    try:
        count = sum(int(qty) for qty in cart.values())
    except (AttributeError, ValueError, TypeError):
        count = 0
    return {"cart_count": count}
