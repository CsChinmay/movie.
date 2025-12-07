from django import template

register = template.Library()

@register.filter(name="split")
def split(value, sep=None):
    if value is None:
        return []
    if sep is None or sep == "":
        return value.split()
    try:
        return value.split(sep)
    except Exception:
        return [value]

@register.filter(name="get_item")
def get_item(obj, key):
    """
    Safe get: works for dicts and objects.
    Usage in template: {{ movie|get_item:"poster_path" }}
    """
    if obj is None:
        return None
    # dict-like
    try:
        if isinstance(obj, dict):
            return obj.get(key)
    except Exception:
        pass
    # attribute-like
    try:
        return getattr(obj, key)
    except Exception:
        pass
    # mapping access fallback
    try:
        return obj[key]
    except Exception:
        return None
