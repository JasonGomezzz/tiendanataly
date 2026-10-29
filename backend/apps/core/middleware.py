class PermissionsPolicyMiddleware:
    """Desactiva APIs del navegador que la tienda no necesita."""

    POLICY = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Permissions-Policy", self.POLICY)
        return response
