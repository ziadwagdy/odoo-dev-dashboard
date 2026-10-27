{
    'name': 'Dashboard Login',
    'summary': 'Passwordless "log in as" for users of the CNC dev dashboard',
    'description': """
The CNC dev dashboard issues a short-lived (60 s), one-time, HMAC-signed link for a
logged-in dashboard user. This module validates the link and opens an Odoo session
for the requested user, so nobody needs a shared Odoo password.

Odoo's own authentication rules still apply afterwards (record rules, MFA if the
user has it enabled). Works unchanged on Odoo 17, 18 and 19.
""",
    'version': '1.0',
    'category': 'Hidden',
    'depends': ['base', 'web'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
}
