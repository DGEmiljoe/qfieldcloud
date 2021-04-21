from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from qfieldcloud.core import permissions_utils, utils
from qfieldcloud.core.models import Project, ProjectQueryset
from qfieldcloud.core.serializers import ProjectSerializer
from rest_framework import generics, permissions, viewsets

User = get_user_model()


class ProjectViewSetPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if view.action == "retrieve":
            # The queryset is already filtered by what the user can see
            return True

        if view.action == "destroy":
            return obj.user_role in permissions_utils.ROLES_CAN_DELETE_PROJECT

        if view.action in ["update", "partial_update"]:
            return obj.user_role in permissions_utils.ROLES_CAN_UPDATE_PROJECT

        raise Exception(f"Unknown object action : {view.action}")

    def has_permission(self, request, view):
        if view.action == "list":
            # The queryset is already filtered by what the user can see
            return True

        if view.action == "create":
            user = request.user
            owner = permissions_utils.get_param_from_request(request, "owner")
            owner_obj = User.objects.get(username=owner) if owner else user
            return permissions_utils.can_create_project(user, owner_obj)

        if view.action in ["retrieve", "destroy", "update", "partial_update"]:
            # These are checked at object level
            return True

        raise Exception(f"Unknown view action : {view.action}")


include_public_param = openapi.Parameter(
    "include-public",
    openapi.IN_QUERY,
    description="Include public projects",
    type=openapi.TYPE_BOOLEAN,
)


@method_decorator(
    name="retrieve",
    decorator=swagger_auto_schema(
        operation_description="Get a project",
        operation_id="Get a project",
    ),
)
@method_decorator(
    name="update",
    decorator=swagger_auto_schema(
        operation_description="Update a project",
        operation_id="Update a project",
    ),
)
@method_decorator(
    name="partial_update",
    decorator=swagger_auto_schema(
        operation_description="Patch a project",
        operation_id="Patch a project",
    ),
)
@method_decorator(
    name="destroy",
    decorator=swagger_auto_schema(
        operation_description="Delete a project",
        operation_id="Delete a project",
    ),
)
@method_decorator(
    name="list",
    decorator=swagger_auto_schema(
        operation_description="""List projects owned by the authenticated
        user or that the authenticated user has explicit permission to access
        (i.e. she is a project collaborator)""",
        operation_id="List projects",
        manual_parameters=[include_public_param],
    ),
)
@method_decorator(
    name="create",
    decorator=swagger_auto_schema(
        operation_description="""Create a new project owned by the specified
        user or organization""",
        operation_id="Create a project",
    ),
)
class ProjectViewSet(viewsets.ModelViewSet):

    serializer_class = ProjectSerializer
    lookup_url_kwarg = "projectid"
    permission_classes = [permissions.IsAuthenticated, ProjectViewSetPermissions]

    def get_queryset(self):
        include_public = False
        include_public_param = self.request.query_params.get(
            "include-public", default=None
        )
        if include_public_param and include_public_param.lower() == "true":
            include_public = True

        projects = Project.objects.for_user(self.request.user)
        if not include_public:
            projects = projects.exclude(
                user_role_origin=ProjectQueryset.RoleOrigins.PUBLIC
            )
        return projects

    def destroy(self, request, projectid):
        # Delete files from storage
        bucket = utils.get_s3_bucket()
        prefix = utils.safe_join("projects/{}/".format(projectid))
        bucket.objects.filter(Prefix=prefix).delete()

        return super().destroy(request, projectid)


@method_decorator(
    name="get",
    decorator=swagger_auto_schema(
        operation_description="List public projects",
        operation_id="List public projects",
    ),
)
class PublicProjectsListView(generics.ListAPIView):

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.for_user(self.request.user).filter(is_public=True)
