from core.models import AccessToken

from rest_framework import serializers


class AccessTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = AccessToken
        fields = ('name', 'id')
