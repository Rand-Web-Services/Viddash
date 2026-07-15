import unittest
from unittest import mock

import app as viddash


SAMPLE_VTT = """WEBVTT

00:00:00.000 --> 00:00:06.000
Welcome to this practical guide about audience research and content strategy.

00:00:06.000 --> 00:00:13.000
content strategy. We will turn customer questions into useful videos people can find.

00:00:48.000 --> 00:00:56.000
Start by collecting the exact questions customers ask before they choose a product.

00:04:05.000 --> 00:04:14.000
Now organize those customer questions into topics and publish one clear answer for each topic.

00:04:52.000 --> 00:05:00.000
Measure which answers attract qualified viewers, then improve the content using that evidence.
"""


class YouTubeTranscriptStudioTests(unittest.TestCase):
    def setUp(self):
        self.client = viddash.app.test_client()

    def test_normalization_removes_rolling_caption_overlap(self):
        segments = viddash.normalize_transcript_segments([
            {"start": 0, "end": 2, "text": "Build a useful content strategy"},
            {"start": 2, "end": 4, "text": "content strategy for your audience"},
            {"start": 4, "end": 6, "text": "Build a useful content strategy for your audience today"},
        ])
        self.assertEqual(segments[1]["text"], "for your audience")
        self.assertEqual(segments[2]["text"], "today")
        self.assertEqual(
            " ".join(item["text"] for item in segments),
            "Build a useful content strategy for your audience today",
        )

    def test_intelligence_is_extractive_and_timestamped(self):
        intelligence = viddash.build_transcript_intelligence(
            viddash._parse_vtt_to_segments(SAMPLE_VTT),
            duration=300,
        )
        self.assertGreater(intelligence["stats"]["words"], 30)
        self.assertEqual(intelligence["stats"]["duration_seconds"], 300)
        self.assertGreaterEqual(len(intelligence["chapters"]), 2)
        self.assertTrue(intelligence["key_moments"])
        self.assertTrue(all("start" in item for item in intelligence["paragraphs"]))
        for moment in intelligence["key_moments"]:
            self.assertIn(moment["text"], intelligence["transcript"])

    def test_endpoint_builds_a_free_caption_project(self):
        captions_result = {
            "success": True,
            "duration": 300,
            "video": {
                "id": "abc123",
                "title": "A useful guide",
                "channel": "Example Creator",
                "thumbnail": "https://i.ytimg.com/example.jpg",
                "webpage_url": "https://www.youtube.com/watch?v=abc123",
                "duration": 300,
            },
            "captions": [{"lang": "en", "type": "manual", "data": SAMPLE_VTT}],
        }
        with mock.patch.object(viddash, "get_current_user", return_value={"id": None, "plan": "free"}), mock.patch.object(
            viddash, "get_youtube_transcripts_used_today", return_value=0
        ), mock.patch.object(viddash, "extract_captions_from_video", return_value=captions_result):
            response = self.client.post(
                "/api/youtube-transcript-studio",
                json={"url": "https://youtu.be/abc123", "language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["source"], "manual_captions")
        self.assertEqual(payload["source_label"], "Creator captions")
        self.assertEqual(payload["remaining_free_today"], 2)
        self.assertEqual(payload["video"]["url"], "https://www.youtube.com/watch?v=abc123")
        self.assertNotIn("content strategy content strategy", payload["transcript"].lower())

    def test_free_limit_is_checked_before_processing(self):
        with mock.patch.object(viddash, "get_current_user", return_value={"id": 42, "plan": "free"}), mock.patch.object(
            viddash, "get_youtube_transcripts_used_today", return_value=3
        ), mock.patch.object(viddash, "extract_captions_from_video") as extractor:
            response = self.client.post(
                "/api/youtube-transcript-studio",
                json={"url": "https://www.youtube.com/watch?v=abc123"},
            )
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["error"], "free_limit_reached")
        extractor.assert_not_called()

    def test_managed_caption_fallback_handles_blocked_server_extraction(self):
        managed_result = {
            "success": True,
            "segments": viddash._parse_vtt_to_segments(SAMPLE_VTT),
            "language": "en",
            "generated": False,
        }
        with mock.patch.object(viddash, "get_current_user", return_value={"id": None, "plan": "free"}), mock.patch.object(
            viddash, "get_youtube_transcripts_used_today", return_value=0
        ), mock.patch.object(
            viddash,
            "extract_captions_from_video",
            return_value={"success": False, "captions": [], "error": "Failed to fetch video info"},
        ), mock.patch.object(
            viddash, "fetch_supadata_transcript", return_value=managed_result
        ) as managed:
            response = self.client.post(
                "/api/youtube-transcript-studio",
                json={"url": "https://www.youtube.com/shorts/abc123", "language": "en"},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["source"], "managed_captions")
        self.assertEqual(payload["video"]["id"], "abc123")
        managed.assert_called_once_with(
            "https://www.youtube.com/shorts/abc123",
            "en",
            allow_generate=False,
        )

    def test_rejects_non_youtube_urls(self):
        with mock.patch.object(viddash, "get_current_user", return_value={"id": 42, "plan": "pro"}):
            response = self.client.post(
                "/api/youtube-transcript-studio",
                json={"url": "https://example.com/video"},
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["error"], "invalid_youtube_url")


if __name__ == "__main__":
    unittest.main()
