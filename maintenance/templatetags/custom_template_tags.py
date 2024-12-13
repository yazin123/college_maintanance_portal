from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    return float(value) * float(arg)

@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0