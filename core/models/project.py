from uuid import uuid4
from django.db import models
from django.db.models import Q
from django.utils import timezone
from core.models.application import Application
from core.models.link import ExternalLink
from core.models.instance import Instance
from core.models.group import Group
from core.models.volume import Volume


class Project(models.Model):

    """
    A Project is an abstract container of (0-to-many):
      * Application
      * Instance
      * Volume
    """
    uuid = models.UUIDField(default=uuid4, unique=True, editable=False)
    name = models.CharField(max_length=256)
    description = models.TextField(blank=True)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    owner = models.ForeignKey(Group, related_name="projects")
    created_by = models.ForeignKey('AtmosphereUser', related_name="projects")
    applications = models.ManyToManyField(Application, related_name="projects",
                                          blank=True)
    links = models.ManyToManyField(ExternalLink, related_name="projects",
                                          blank=True)

    @staticmethod
    def shared_with_user(user, is_leader=None):
        """
        is_leader: Explicitly filter out instances if `is_leader` is True/False, if None(default) do not test for project leadership.
        """
        owner_query = Q(created_by=user)
        leadership_query = Q(owner__memberships__user=user)
        if is_leader == False:
            leadership_query &= Q(owner__memberships__is_leader=False)
        elif is_leader == True:
            leadership_query &= Q(owner__memberships__is_leader=True)
        return Project.objects.filter(owner_query | leadership_query)

    def active_volumes(self):
        return self.volumes.model.active_volumes.filter(
            pk__in=self.volumes.values_list("id"))

    def active_instances(self):
        return self.instances.model.active_instances.filter(
            pk__in=self.instances.values_list("id"))

    def has_shared_resources(self, current_user=None):
        if not current_user:
            current_user = self.created_by
        has_shared_volumes = self.active_volumes().filter(~Q(instance_source__created_by=current_user)).count() > 0
        has_shared_instances = self.active_instances().filter(~Q(created_by=current_user)).count() > 0
        return has_shared_volumes or has_shared_instances

    def get_users(self):
        return self.owner.user_set.all()

    def get_leaders(self):
        from core.models import AtmosphereUser
        leaders = self.owner.get_leaders()
        if not leaders:
            leaders = AtmosphereUser.objects.filter(username=self.created_by.username)
        return leaders

    def __unicode__(self):
        return "Name:%s Owner:%s" \
            % (self.name, self.owner)

    def has_running_resources(self):
        now_date = timezone.now()
        if any(not instance.end_date or instance.end_date >= now_date
               for instance in self.instances.all()):
            return True
        if any(not volume.end_date or volume.end_date >= now_date
               for volume in self.volumes.all()):
            return True

    def remove_object(self, related_obj):
        """
        Use this function to move A single object
        to Project X
        """
        if hasattr(related_obj, 'project'):
            related_obj.project = None
            related_obj.save()
            return
        return related_obj.projects.remove(self)

    def add_object(self, related_obj):
        """
        Use this function to move A single object
        to Project X
        """
        if isinstance(related_obj, Instance):
            instance = related_obj
            self._test_project_ownership(instance.created_by)
            instance.project = self
            instance.save()
        elif isinstance(related_obj, Volume):
            volume = related_obj
            self._test_project_ownership(volume.instance_source.created_by)
            volume.project = self
            volume.save()
        elif isinstance(related_obj, Application):
            application = related_obj
            self._test_project_ownership(application.created_by)
            self.applications.add(related_obj)
        else:
            raise Exception("Invalid type for Object %s: %s"
                            % (related_obj, type(related_obj)))

    def _test_project_ownership(self, user):
        group = self.owner
        if user in group.user_set.all():
            return True
        raise Exception(
            "User:%s does NOT belong to Group:%s" % (user, group))

    def copy_objects(self, to_project):
        """
        Use this function to move ALL objects
        from Project X to Project Y
        """
        [to_project.add_object(app) for app in self.applications.all()]
        [to_project.add_object(inst) for inst in self.instances.all()]
        [to_project.add_object(vol) for vol in self.volumes.all()]

    def delete_project(self):
        """
        Use this function to remove Project X
        from all objects using it before removing
        the entire Project
        """
        [self.remove_object(app) for app in self.applications.all()]
        [self.remove_object(inst) for inst in self.instances.all()]
        [self.remove_object(vol) for vol in self.volumes.all()]
        self.end_date = timezone.now()
        self.save()

    class Meta:
        db_table = 'project'
        app_label = 'core'
