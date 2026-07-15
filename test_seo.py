import json
import re
import unittest

import app as viddash


class SeoFoundationTests(unittest.TestCase):
    def setUp(self):
        self.client = viddash.app.test_client()

    def test_audio_editor_has_indexing_social_and_answer_schema(self):
        response = self.client.get("/audio-editor")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)

        self.assertIn('name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"', body)
        self.assertIn('property="og:url" content="https://viddash.app/audio-editor"', body)
        self.assertEqual(body.count('rel="canonical"'), 1)

        scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.DOTALL)
        self.assertEqual(len(scripts), 1)
        schema = json.loads(scripts[0])
        types = {item["@type"] for item in schema["@graph"]}
        self.assertTrue({"Organization", "WebSite", "WebApplication", "BreadcrumbList", "FAQPage"}.issubset(types))

        faq = next(item for item in schema["@graph"] if item["@type"] == "FAQPage")
        for item in faq["mainEntity"]:
            self.assertIn(item["name"], body)
            self.assertIn(item["acceptedAnswer"]["text"], body)

    def test_every_answer_hub_faq_matches_visible_page_content(self):
        for path, expected_faqs in viddash.SEO_PAGE_FAQS.items():
            with self.subTest(path=path):
                body = self.client.get(f"/{path}").get_data(as_text=True)
                scripts = re.findall(r'<script type="application/ld\+json">(.*?)</script>', body, re.DOTALL)
                self.assertEqual(len(scripts), 1)
                schema = json.loads(scripts[0])
                faq = next(item for item in schema["@graph"] if item["@type"] == "FAQPage")
                actual = [
                    (item["name"], item["acceptedAnswer"]["text"])
                    for item in faq["mainEntity"]
                ]
                self.assertEqual(actual, expected_faqs)
                for question, answer in expected_faqs:
                    self.assertIn(question, body)
                    self.assertIn(answer, body)

    def test_auth_and_unfinished_documentation_pages_are_noindex(self):
        for path in ("/login", "/signup", "/api-documentation"):
            with self.subTest(path=path):
                body = self.client.get(path).get_data(as_text=True)
                self.assertIn('name="robots" content="noindex,follow"', body)
                self.assertNotIn('type="application/ld+json"', body)

    def test_incomplete_locales_remain_accessible_but_are_not_indexed(self):
        response = self.client.get("/es/audio-editor")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('<html lang="es"', body)
        self.assertIn('name="robots" content="noindex,follow"', body)
        self.assertNotIn('type="application/ld+json"', body)

    def test_sitemap_contains_only_indexable_public_pages(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("<loc>https://viddash.app/audio-editor</loc>", body)
        self.assertNotIn("<loc>https://viddash.app/login</loc>", body)
        self.assertNotIn("<loc>https://viddash.app/signup</loc>", body)
        self.assertNotIn("<loc>https://viddash.app/api-documentation</loc>", body)
        self.assertNotIn("<loc>https://viddash.app/es/", body)

    def test_robots_reduces_private_and_api_crawling(self):
        body = self.client.get("/robots.txt").get_data(as_text=True)
        for path in ("/admin", "/account", "/api/", "/auth/", "/billing/"):
            self.assertIn(f"Disallow: {path}", body)
        self.assertIn("Sitemap: https://viddash.app/sitemap.xml", body)

    def test_every_public_page_has_a_complete_rendered_search_head(self):
        for path in viddash.PUBLIC_PAGES:
            url = f"/{path}" if path else "/"
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                body = response.get_data(as_text=True)
                self.assertEqual(len(re.findall(r"<title>.+?</title>", body, re.DOTALL)), 1)
                self.assertEqual(len(re.findall(r'<meta name="description"', body)), 1)
                self.assertEqual(body.count('rel="canonical"'), 1)
                self.assertGreaterEqual(len(re.findall(r"<h1(?:\s|>)", body)), 1)


if __name__ == "__main__":
    unittest.main()
