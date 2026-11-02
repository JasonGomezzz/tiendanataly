from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api import ScopedThrottleMixin

from . import places

MIN_CHARS = 4
MAX_CHARS = 120


class PlacesBase(ScopedThrottleMixin, APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_scope = "places"

    def _check(self, request):
        """Valida que el buscador esté activo y que `session` sea un UUID. Devuelve (session, error)."""
        if not places.enabled():
            return None, Response({"detail": "Las direcciones sugeridas no están activas."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        session = request.query_params.get("session", "")
        if not places.SESSION_RE.match(session):
            return None, Response({"detail": "Falta la sesión de búsqueda."}, status=status.HTTP_400_BAD_REQUEST)
        return session, None


class PlacesAutocompleteView(PlacesBase):
    """Sugerencias de dirección mientras la clienta escribe. Si Google falla, devuelve lista vacía (el checkout sigue)."""

    def get(self, request):
        session, error = self._check(request)
        if error:
            return error
        query = " ".join(request.query_params.get("q", "").split())
        if len(query) < MIN_CHARS:
            return Response({"detail": f"Escribe al menos {MIN_CHARS} letras."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            suggestions = places.autocomplete(query[:MAX_CHARS], session)
        except places.PlacesUnavailable:
            return Response({"sugerencias": []})
        return Response({"sugerencias": suggestions})


class PlacesDetailView(PlacesBase):
    """Datos del lugar elegido, ya separados en departamento, provincia, distrito y dirección."""

    def get(self, request):
        session, error = self._check(request)
        if error:
            return error
        place_id = request.query_params.get("id", "")
        if not places.PLACE_ID_RE.match(place_id):
            return Response({"detail": "Lugar no válido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            data = places.place_details(place_id, session)
        except places.PlacesUnavailable:
            return Response({"detail": "No pudimos obtener la dirección. Escríbela a mano."}, status=status.HTTP_502_BAD_GATEWAY)
        if data is None:
            return Response({"detail": "Escribe la dirección a mano."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        return Response(data)
