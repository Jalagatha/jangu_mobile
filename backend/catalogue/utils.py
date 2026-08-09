from django.utils.text import slugify


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
