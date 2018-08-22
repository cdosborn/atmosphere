from django.db import models
from django.utils import timezone

from django_cyverse_auth.models import Token


class AccessToken(models.Model):
    """
    Extend the django_cyverse_auth Token to add a name
    """
    token = models.OneToOneField(Token, on_delete=models.CASCADE)
    name = models.CharField(max_length=128, null=False, blank=False)

    class Meta:
        db_table = "access_token"
        app_label = "core"

def create_access_token(user, token_name=None, token_expire=None, remote_ip=None, issuer=None):
    token = Token(user=user)
    token.save()
    access_token, created = AccessToken.objects.update_or_create(token=token, name=token_name)
    return access_token
