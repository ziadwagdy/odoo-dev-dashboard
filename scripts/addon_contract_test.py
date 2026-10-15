import base64, hashlib, hmac, json, os, re, subprocess, sys, time, urllib.request, urllib.error, http.cookiejar
DB = 'zz-sso-test'; PORT = 18999
conf = open('/etc/odoo/odoo.conf').read()
master = re.search(r'(?m)^admin_passwd\s*=\s*(.+)$', conf).group(1).strip()
addons = re.search(r'(?m)^addons_path\s*=\s*(.+)$', conf).group(1).strip()
cmd = ['odoo', '-c', '/etc/odoo/odoo.conf', '--addons-path', addons + ',/tmp/dashboard-addons',
       '-d', DB, '-i', 'base,dashboard_login', '--without-demo=all', '--workers=0',
       '--http-port', str(PORT), '--gevent-port', str(PORT + 1), '--max-cron-threads=0', '--log-level=warn']
log = open('/tmp/sso-server.log', 'w')
srv = subprocess.Popen(cmd, stdout=log, stderr=log)

def main():
    for _ in range(240):
        try:
            urllib.request.urlopen('http://127.0.0.1:%d/web/health' % PORT, timeout=2); break
        except Exception:
            time.sleep(2)
    else:
        print('server did not start'); print(open('/tmp/sso-server.log').read()[-1500:]); return
    key = hashlib.sha256(('dashboard-sso:' + master).encode()).digest()

    def token(login='admin', db=DB, ttl=60, iat=None):
        now = int(time.time()) if iat is None else iat
        payload = {'db': db, 'login': login, 'iat': now, 'exp': now + ttl, 'n': os.urandom(8).hex()}
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        return body + '.' + hmac.new(key, body.encode(), hashlib.sha256).hexdigest()

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    def hit(t, extra=''):
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(NoRedirect, urllib.request.HTTPCookieProcessor(cj))
        try:
            r = op.open('http://127.0.0.1:%d/dashboard/login?db=%s&t=%s%s' % (PORT, DB, t, extra), timeout=60)
            return r.status, r.headers.get('Location'), cj
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get('Location'), cj

    def authed(cj):
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        r = op.open('http://127.0.0.1:%d/web' % PORT, timeout=90)
        body = r.read().decode('utf-8', 'replace')
        return 'landed on login page' if '/web/login' in r.geturl() else ('web client loaded' if 'session_info' in body or 'odoo' in body.lower() else 'unknown')

    s, loc, cj = hit(token())
    print('%-26s %s %s -> %s' % ('valid link', s, loc, authed(cj)))
    t = token(); hit(t)
    print('%-26s %s' % ('replay of same link', hit(t)[0]))
    print('%-26s %s' % ('tampered signature', hit(token()[:-4] + 'abcd')[0]))
    print('%-26s %s' % ('expired link', hit(token(iat=int(time.time()) - 600))[0]))
    print('%-26s %s' % ('ttl too long', hit(token(ttl=3600))[0]))
    print('%-26s %s' % ('unknown user', hit(token(login='nobody-here'))[0]))
    print('%-26s %s' % ('wrong db in token', hit(token(db='other'))[0]))
    s, loc, _ = hit(token(), '&redirect=//evil.example')
    print('%-26s %s %s' % ('open redirect blocked', s, loc))

try:
    main()
finally:
    srv.terminate()
    try:
        srv.wait(30)
    except Exception:
        srv.kill()
