from core.models import AccessToken

from rest_framework import serializers


class AccessTokenSerializer(serializers.ModelSerializer):
    expireTime = serializers.ReadOnlyField(source='token.expireTime')

    class Meta:
        model = AccessToken
        fields = ('name', 'expireTime', 'id')
