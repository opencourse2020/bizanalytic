"""
Custom template tags and filters for LogiFlex reports.

Usage in template:
  {% load report_tags %}
  {% with is_flagged=driver.driver_name|in_list:flagged_names %}

Place this file at:
  your_app/templatetags/report_tags.py

And create an empty __init__.py in templatetags/ if it doesn't exist.
"""

from django import template

register = template.Library()


@register.filter(name='in_list')
def in_list(value, the_list):
    """
    Returns True if value is in the_list.
    Handles both Python lists and None gracefully.

    Usage: {{ item|in_list:some_list }}
    """
    if the_list is None:
        return False
    if isinstance(the_list, (list, tuple)):
        return value in the_list
    return False


@register.filter(name='score_color')
def score_color(value):
    """
    Returns a CSS color variable name based on a score value.
    Usage: {{ dim.score|score_color }}
    """
    try:
        score = float(value)
    except (ValueError, TypeError):
        return 'var(--ink-tertiary)'

    if score >= 70:
        return 'var(--green)'
    elif score >= 50:
        return 'var(--amber)'
    else:
        return 'var(--red)'


@register.filter(name='multiply')
def multiply(value, arg):
    """
    Multiplies value by arg. Used for percentage widths.
    Usage: {{ dim.score|multiply:1 }}%
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
