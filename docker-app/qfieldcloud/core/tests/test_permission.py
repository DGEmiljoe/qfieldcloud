import logging

from qfieldcloud.core.models import (
    AuthToken,
    Organization,
    Project,
    ProjectCollaborator,
    User,
)
from rest_framework import status
from rest_framework.test import APITestCase

from .utils import testdata_path

logging.disable(logging.CRITICAL)


class QfcTestCase(APITestCase):
    def setUp(self):
        # Create a user
        self.user1 = User.objects.create_user(username="user1", password="abc123")
        self.token1 = AuthToken.objects.get_or_create(user=self.user1)[0]

        # Create a second user
        self.user2 = User.objects.create_user(username="user2", password="abc123")
        self.token2 = AuthToken.objects.get_or_create(user=self.user2)[0]

        # Create an organization
        self.organization1 = Organization.objects.create(
            username="organization1",
            password="abc123",
            user_type=2,
            organization_owner=self.user1,
        )

        # Create a project
        self.project1 = Project.objects.create(
            name="project1", is_public=False, owner=self.user1
        )
        self.project1.save()

    def tearDown(self):
        # Remove all projects avoiding bulk delete in order to use
        # the overrided delete() function in the model
        for p in Project.objects.all():
            p.delete()

            User.objects.all().delete()
            # Remove credentials
            self.client.credentials()

    def test_collaborator_project_takeover(self):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token1.key)

        response = self.client.get("/api/v1/projects/", format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(1, len(response.data))
        self.assertEqual("project1", response.data[0].get("name"))

        project = Project.objects.get(pk=response.data[0].get("id"))

        response = self.client.patch(
            f"/api/v1/projects/{project.pk}/",
            {"name": "renamed-project", "owner": "user1"},
        )
        self.assertTrue(status.is_success(response.status_code))

        # user2 doesn't get to see user1's project
        self.client.logout()

        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token2.key)
        response = self.client.get("/api/v1/projects/", format="json")
        self.assertEqual(0, len(response.data))

        # user2 is added to the org
        ProjectCollaborator.objects.create(
            project=project,
            collaborator=self.user2,
            role=ProjectCollaborator.Roles.READER,
        )
        response = self.client.get("/api/v1/projects/", format="json")
        self.assertEqual(1, len(response.data))
        self.assertEqual("renamed-project", response.data[0].get("name"))

        # patch is denied
        response = self.client.patch(
            f"/api/v1/projects/{project.pk}/",
            {"name": "stolen-project", "owner": "user2"},
        )
        self.assertFalse(status.is_success(response.status_code))
        project.refresh_from_db()
        self.assertEqual("renamed-project", project.name)

    def test_reader_cannot_push(self):
        # Connect as user2
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token2.key)

        # Set user2 as a collaborator READER of project1
        self.collaborator1 = ProjectCollaborator.objects.create(
            project=self.project1,
            collaborator=self.user2,
            role=ProjectCollaborator.Roles.READER,
        )

        file_path = testdata_path("file.txt")
        # Push a file
        response = self.client.post(
            "/api/v1/files/{}/file.txt/".format(self.project1.id),
            {"file": open(file_path, "rb")},
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_reporter_can_push(self):
        # Connect as user2
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token2.key)

        # Set user2 as a collaborator REPORTER of project1
        self.collaborator1 = ProjectCollaborator.objects.create(
            project=self.project1,
            collaborator=self.user2,
            role=ProjectCollaborator.Roles.REPORTER,
        )

        file_path = testdata_path("file.txt")
        # Push a file
        response = self.client.post(
            "/api/v1/files/{}/file.txt/".format(self.project1.id),
            {"file": open(file_path, "rb")},
            format="multipart",
        )
        self.assertTrue(status.is_success(response.status_code))

    def test_cannot_list_files_of_private_project(self):
        # Connect as user2
        self.client.credentials(HTTP_AUTHORIZATION="Token " + self.token2.key)

        # List files
        response = self.client.get("/api/v1/files/{}/".format(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
