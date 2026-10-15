def client_ip(request):
    """Real client address. The platform is reachable only through the Cloudflare tunnel,
    which sets CF-Connecting-IP; fall back to X-Forwarded-For then the socket peer."""
    meta = request.META
    return (meta.get('HTTP_CF_CONNECTING_IP')
            or meta.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
            or meta.get('REMOTE_ADDR', ''))
