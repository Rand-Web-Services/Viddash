import io
import json
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from werkzeug.datastructures import MultiDict

import app as viddash


class AudioEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tempdir = tempfile.TemporaryDirectory(prefix="viddash_audio_test_")
        cls.sources = []
        ffmpeg = viddash._find_media_binary("ffmpeg")
        for index, frequency in enumerate((330, 550)):
            path = os.path.join(cls.tempdir.name, f"tone_{index}.wav")
            subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "lavfi", "-i", f"sine=frequency={frequency}:duration=2",
                    "-c:a", "pcm_s16le", path,
                ],
                check=True,
            )
            cls.sources.append(path)

    @classmethod
    def tearDownClass(cls):
        cls.tempdir.cleanup()

    def setUp(self):
        self.user_patch = mock.patch.object(
            viddash,
            "get_current_user",
            return_value={"id": None, "plan": "pro"},
        )
        self.user_patch.start()
        self.client = viddash.app.test_client()

    def tearDown(self):
        self.user_patch.stop()

    def _request(self, edits, cleanup="studio"):
        data = MultiDict()
        for index, path in enumerate(self.sources):
            with open(path, "rb") as source:
                data.add("files", (io.BytesIO(source.read()), f"track-{index}.wav"))
        data.add("edits", json.dumps(edits))
        data.add("cleanup", cleanup)
        data.add("format", "mp3")
        return self.client.post("/api/audio/edit", data=data, content_type="multipart/form-data")

    def test_merges_trims_and_cleans_two_tracks(self):
        response = self._request([
            {"start": 0.2, "end": 1.2},
            {"start": 0.0, "end": 0.8},
        ])
        self.assertEqual(response.status_code, 200, f"Unexpected HTTP {response.status_code}")
        self.assertEqual(response.mimetype, "audio/mpeg")
        self.assertGreater(len(response.data), 10_000)

        output = os.path.join(self.tempdir.name, "result.mp3")
        output_data = response.data
        response.close()
        with open(output, "wb") as destination:
            destination.write(output_data)
        duration = viddash._probe_audio_duration(output)
        self.assertAlmostEqual(duration, 1.8, delta=0.15)

    def test_rejects_trim_past_track_duration(self):
        response = self._request([
            {"start": 0, "end": 9},
            {"start": 0, "end": 1},
        ], cleanup="off")
        self.assertEqual(response.status_code, 400)
        self.assertIn("trim must stay within", response.get_json()["error"])

    def test_accepts_unknown_browser_duration_as_full_track(self):
        response = self._request([
            {"start": 0.5, "end": None},
            {"start": 0, "end": 0.5},
        ], cleanup="off")
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_free_account_is_limited_after_three_successful_exports(self):
        with mock.patch.object(viddash, "get_current_user", return_value={"id": 42, "plan": "free"}), mock.patch.object(
            viddash, "get_audio_edits_used_today", return_value=3
        ):
            response = self.client.post("/api/audio/edit")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.get_json()["error"], "free_limit_reached")


if __name__ == "__main__":
    unittest.main()
