from rest_framework import status
from rest_framework.response import Response

from core.models import AccessToken, AtmosphereUser
from core.models.access_token import create_access_token
from core.query import only_current_access_tokens

from api.exceptions import invalid_auth
from api.v2.serializers.details import AccessTokenSerializer
from api.v2.views.base import AuthModelViewSet

class AccessTokenViewSet(AuthModelViewSet):

    """
    API endpoint that allows AccessTokens to be viewed or edited.
    """
    serializer_class = AccessTokenSerializer

    def get_queryset(self):
        """
        Filter projects by current user.
        """
        user = self.request.user
        qs = AccessToken.objects.filter(token__user=user)
        if 'archived' in self.request.query_params:
            return qs
        # Return current results
        return qs.filter(only_current_access_tokens())

    def create(self, request):
        issuer_backend = request.session.get('_auth_user_backend', '').split('.')[-1]
        data = request.data
        name = data.get('name', None)
        atmo_user = data.get('atmo_user', None)
        if not atmo_user:
            return invalid_auth("atmo_user missing")

        user = AtmosphereUser.objects.get(id=atmo_user)
        access_token = create_access_token(user, name, issuer=issuer_backend)
        json_response = {
            'token': access_token.token_id,
            'id': access_token.id,
            'name': name
        }
        return Response(json_response, status=status.HTTP_201_CREATED)
