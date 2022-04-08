from json import JSONDecodeError

from django.conf import settings
from django.db import models
import hvac
import hvac.exceptions
import json

from web_interface.apps.system import parameter_manager


class Project(models.Model):
    DEFAULT_AUTH_OPTIONS = """{"auth_required": false, "auth_setting": "{}"}"""

    name = models.CharField(max_length=255)
    # Stored as CSV, contains a list of tests/test categories to run
    comment = models.CharField(max_length=1000)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, through="project.ProjectPermission")
    # ?TODO refactor 'options' field to json field
    _options = models.CharField(max_length=4000, default=DEFAULT_AUTH_OPTIONS)
    version = models.CharField(max_length=255, default="")
    contact = models.CharField(max_length=255, default="")
    company = models.CharField(max_length=255, default="")
    testers = models.CharField(max_length=255, default="")
    visual_impairments = models.BooleanField(default=False)
    url = models.CharField(max_length=255, default="")
    audit_report = models.CharField(max_length=4000, default="")
    vpat_report = models.CharField(max_length=4000, default="")
    test_list = models.CharField(max_length=4000, default="")
    last_test = models.DateTimeField(null=True, blank=True)
    request_interval = models.IntegerField(default=0)
    page_after_login = models.BooleanField(default=False)
    enable_content_blocking = models.BooleanField(default=True)
    enable_popup_detection = models.BooleanField(default=False)
    disable_parallel_testing = models.BooleanField(default=False)
    disclaimer = models.CharField(max_length=8192, null=True, blank=True)
    created_stamp = models.DateTimeField(auto_now_add=True)
    updated_stamp = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "project"

    def __str__(self):
        return f"{self.__class__.__name__} object (name: {self.name}) (company: {self.company}) (pk: {self.pk})"

    @property
    def has_activities(self) -> bool:
        from web_interface.apps.activity.models import Activity

        activities_qs = Activity.objects.filter(page__project=self)
        return activities_qs.exists()

    @property
    def options(self) -> str:
        try:
            decoded_value = json.loads(self._options)
            decoded_value["auth_setting"] = json.loads(decoded_value["auth_setting"])
            if "password" in decoded_value["auth_setting"]:
                if decoded_value["auth_setting"]["password"] == "#project_auth_password":
                    try:
                        vcl = hvac.Client(url=parameter_manager.get_parameter("VAULT_URL"), namespace=parameter_manager.get_parameter("VAULT_NAMESPACE"))
                        if parameter_manager.get_parameter("VAULT_ROLE_ID") is not None:
                            vcl.auth.approle.login(
                                role_id=parameter_manager.get_parameter("VAULT_ROLE_ID"), secret_id=parameter_manager.get_parameter("VAULT_SECRET_ID")
                            )
                        else:
                            print("Defaulting to debug token")
                            vcl.token = "root"
                        response = vcl.secrets.kv.read_secret_version(path=f"project_auth_password/{self.pk}")
                        decoded_value["auth_setting"]["password"] = response["data"]["data"]["auth_password"]
                    except hvac.exceptions.InvalidPath:
                        return self._options
            decoded_value["auth_setting"] = json.dumps(decoded_value["auth_setting"])
            return json.dumps(decoded_value)
        except (JSONDecodeError, TypeError, KeyError):
            return Project.DEFAULT_AUTH_OPTIONS

    @options.setter
    def options(self, value):
        try:
            decoded_value = json.loads(value)
            decoded_value["auth_setting"] = json.loads(decoded_value["auth_setting"])

            if "password" in decoded_value["auth_setting"]:
                vcl = hvac.Client(url=parameter_manager.get_parameter("VAULT_URL"), namespace=parameter_manager.get_parameter("VAULT_NAMESPACE"))
                if parameter_manager.get_parameter("VAULT_ROLE_ID") is not None:
                    vcl.auth.approle.login(role_id=parameter_manager.get_parameter("VAULT_ROLE_ID"), secret_id=parameter_manager.get_parameter("VAULT_SECRET_ID"))
                else:
                    vcl.token = "root"
                vcl.secrets.kv.v2.create_or_update_secret(
                    path=f"project_auth_password/{self.pk}",
                    secret={"auth_password": decoded_value["auth_setting"]["password"]},
                )

            decoded_value["auth_setting"] = json.dumps(decoded_value["auth_setting"])

            self._options = json.dumps(decoded_value)
        except (JSONDecodeError, TypeError, KeyError):
            self._options = Project.DEFAULT_AUTH_OPTIONS


class ProjectRole(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        db_table = "project_role"

    def __str__(self):
        return f"{self.__class__.__name__} object (name: {self.name}) (pk: {self.pk})"


class ProjectPermission(models.Model):
    project = models.ForeignKey(Project, related_name="project_permissions", on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="project_permissions", on_delete=models.CASCADE
    )
    role = models.ForeignKey(ProjectRole, related_name="project_permissions", on_delete=models.PROTECT)

    class Meta:
        db_table = "project_permission"
        unique_together = ("project", "user", "role")

    def __str__(self):
        return (
            f"{self.__class__.__name__} object "
            f"(project_id: {self.project_id}) (user_id: {self.user_id}) (role_id: {self.role_id})"
        )
