The `dashboard_login` addon is the source for the shared local development addon
at `$ODOO_DEV_BASE/dashboard-addons/dashboard_login`, mounted read-only into Odoo
containers as `/mnt/dashboard-addons/dashboard_login`.

After editing this source, synchronize the Python files to that local directory
and restart the affected local Odoo application so its workers reload them.
Never deploy this addon or perform any other write on Odoo.sh.

Run the token regression tests with:

```sh
python3 -m unittest discover -s scripts/tests -p test_dashboard_sso.py
```

The timestamp check permits five seconds of future clock skew. A token's age is
limited by its signed expiry (60 seconds by default), rather than a five-second
maximum age. Database-backed nonce consumption still prevents replay.
