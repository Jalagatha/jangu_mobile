from django.utils.text import slugify

# Display order for variant attributes. Postgres jsonb does not keep the order
# keys were entered in, so labels cannot rely on dict order.
ATTRIBUTE_ORDER = {
    key: rank
    for rank, key in enumerate(["processor", "ram", "storage", "size", "connectivity", "color"])
}


def variant_label(attributes):
    """`{"storage": "128GB", "color": "Black"}` -> `128GB / Black`; empty -> `Standard`."""
    if not isinstance(attributes, dict):
        return "Standard"
    keys = sorted(attributes, key=lambda key: (ATTRIBUTE_ORDER.get(key, len(ATTRIBUTE_ORDER)), key))
    parts = [str(attributes[key]) for key in keys if attributes[key] not in (None, "")]
    return " / ".join(parts) if parts else "Standard"


def unique_slugify(model, value, instance_pk=None):
    """Return a slug for `value` that is unique among `model`'s existing rows."""
    base_slug = slugify(value)
    candidate = base_slug
    suffix = 2
    queryset = model.objects.all()
    if instance_pk is not None:
        queryset = queryset.exclude(pk=instance_pk)
    while queryset.filter(slug=candidate).exists():
        candidate = f"{base_slug}-{suffix}"
        suffix += 1
    return candidate
