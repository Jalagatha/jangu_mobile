from django import forms

from catalogue.models import ProductVariant


class _VariantMixin(forms.Form):
    variant_id = forms.IntegerField(min_value=1)

    def clean_variant_id(self):
        vid = self.cleaned_data["variant_id"]
        variant = (
            ProductVariant.objects.filter(id=vid, product__is_active=True)
            .select_related("product")
            .first()
        )
        if variant is None:
            raise forms.ValidationError("That product is unavailable.")
        self.cleaned_data["variant"] = variant
        return vid


class AddToCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=1, initial=1)


class UpdateCartForm(_VariantMixin):
    quantity = forms.IntegerField(min_value=0)
