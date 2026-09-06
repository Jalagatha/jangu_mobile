from django.test import TestCase
from django.urls import reverse


class IndexPageTests(TestCase):
    def test_root_returns_200_html_unauthenticated(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response["Content-Type"])

    def test_root_uses_index_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "core/index.html")

    def test_root_shows_title_and_docs_link(self):
        response = self.client.get("/")
        content = response.content.decode()
        self.assertIn("Jango Mobile API", content)
        self.assertIn("/api/docs/", content)

    def test_root_shows_version_from_spectacular_settings(self):
        response = self.client.get("/")
        self.assertContains(response, "0.1.0")
