"""
Jinja2-based HTML + plain text email template engine.
Supports smart placeholder rendering with fallback for missing keys.
"""
from jinja2 import Environment, BaseLoader, Undefined
from typing import Dict, Optional
import re

# All supported template variables
TEMPLATE_VARS = {
    'full_name':          'Recipient full name',
    'first_name':         'Recipient first name',
    'certificate_id':     'Unique certificate ID',
    'course_name':        'Certificate / course name',
    'issue_date':         'Date certificate was issued',
    'organization_name':  'Organisation name',
    'verification_link':  'QR verification URL',
    'unsubscribe_link':   'Unsubscribe URL (campaigns only)',
}

# Default certificate dispatch email
DEFAULT_CERT_SUBJECT = "Your {{course_name}} Certificate — {{organization_name}}"

DEFAULT_CERT_BODY = """\
Dear {{first_name}},

Congratulations on successfully completing {{course_name}}!

Please find your personalised certificate attached to this email.

Certificate ID: {{certificate_id}}
Issued: {{issue_date}}

Verify this certificate online:
{{verification_link}}

This certificate is issued by {{organization_name}} as official confirmation \
of your achievement. Please retain it for your records.

Warm regards,
{{organization_name}}\
"""

# Default campaign (no attachment)
DEFAULT_CAMPAIGN_SUBJECT = "Update from {{organization_name}}"

DEFAULT_CAMPAIGN_BODY = """\
Dear {{first_name}},

{{message_body}}

Warm regards,
{{organization_name}}

---
To unsubscribe from future communications: {{unsubscribe_link}}\
"""


class SafeDict(dict):
    """Returns empty string for missing keys instead of raising."""
    def __missing__(self, key):
        return ''


def _jinja_env() -> Environment:
    """Create Jinja2 env with {{ }} delimiters matching our template syntax."""
    env = Environment(
        loader=BaseLoader(),
        variable_start_string='{{',
        variable_end_string='}}',
        undefined=Undefined,
        autoescape=False,
    )
    return env


def render(template: str, context: Dict) -> str:
    """
    Render a template string with context dict.
    Safe — missing keys produce empty string, never raises.
    Supports both {{var}} and {var} styles.
    """
    if not template:
        return ''
    ctx = SafeDict(context)
    try:
        env = _jinja_env()
        tmpl = env.from_string(template)
        return tmpl.render(**ctx)
    except Exception:
        # Fallback: simple string replace
        result = template
        for k, v in context.items():
            result = result.replace('{{' + k + '}}', str(v or ''))
            result = result.replace('{' + k + '}', str(v or ''))
        return result


def build_context(
    user,
    cert_type=None,
    org=None,
    verify_base_url: str = '',
    unsubscribe_base_url: str = '',
) -> Dict:
    """Build full template context from user + cert type + org objects."""
    issue_date = ''
    if user.sent_at:
        issue_date = user.sent_at.strftime('%d %B %Y')

    cert_id = user.certificate_id or ''
    verify_url = f"{verify_base_url}/verify/{cert_id}" if cert_id and verify_base_url else ''
    unsub_url = f"{unsubscribe_base_url}/unsubscribe/{user.id}" if unsubscribe_base_url else ''

    return {
        'full_name':         user.full_name,
        'first_name':        user.first_name,
        'certificate_id':    cert_id,
        'course_name':       cert_type.name if cert_type else '',
        'issue_date':        issue_date,
        'organization_name': org.org_name if org else 'Medical Locum Jobs',
        'verification_link': verify_url,
        'unsubscribe_link':  unsub_url,
    }
