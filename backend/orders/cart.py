from decimal import Decimal

from catalogue.models import ProductVariant

from .exceptions import InsufficientStockError

SESSION_KEY = "cart"


class SessionCart:
    """A shopping cart persisted in ``request.session[SESSION_KEY]`` as
    ``{"<variant_id>": <int quantity>}``. Prices are always resolved live."""

    def __init__(self, request):
        self.session = request.session
        # `.get`, not `.setdefault` — reading a cart on a page that never
        # mutates it (admin, API, every catalogue page) must not write an
        # empty "cart" key into that visitor's session.
        self._items = dict(self.session.get(SESSION_KEY) or {})

    # -- mutation -----------------------------------------------------------
    def _touch(self):
        self.session[SESSION_KEY] = self._items
        self.session.modified = True

    def add(self, variant, qty=1, *, replace=False):
        key = str(variant.id)
        new_qty = qty if replace else self._items.get(key, 0) + qty
        if new_qty > variant.stock_qty:
            raise InsufficientStockError(
                [{"variant": variant, "requested": new_qty, "available": variant.stock_qty}]
            )
        self._items[key] = new_qty
        self._touch()

    def set_quantity(self, variant_id, qty):
        key = str(variant_id)
        if qty <= 0:
            self.remove(variant_id)
            return
        variant = ProductVariant.objects.filter(id=variant_id).first()
        if variant is None:
            self.remove(variant_id)
            return
        if qty > variant.stock_qty:
            raise InsufficientStockError(
                [{"variant": variant, "requested": qty, "available": variant.stock_qty}]
            )
        self._items[key] = qty
        self._touch()

    def remove(self, variant_id):
        if self._items.pop(str(variant_id), None) is not None:
            self._touch()

    def clear(self):
        self._items = {}
        self._touch()

    # -- reads ------------------------------------------------------------
    def __iter__(self):
        ids = [int(k) for k in self._items]
        variants = {v.id: v for v in ProductVariant.objects.filter(id__in=ids)}
        pruned = False
        for key in list(self._items):
            variant = variants.get(int(key))
            if variant is None:
                del self._items[key]
                pruned = True
                continue
            qty = self._items[key]
            yield {
                "variant": variant,
                "quantity": qty,
                "unit_price": variant.price,
                "line_total": variant.price * qty,
            }
        if pruned:
            self._touch()

    def __len__(self):
        return sum(self._items.values())

    @property
    def subtotal(self):
        return sum((line["line_total"] for line in self), Decimal("0"))
