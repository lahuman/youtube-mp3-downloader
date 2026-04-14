import unittest

from youtube_urls import extract_youtube_video_id, is_valid_youtube_url, normalize_youtube_url


VIDEO_ID = "xi7fgg4-ZhY"
CANONICAL_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"


class YoutubeUrlHandlingTests(unittest.TestCase):
    def test_supported_urls_are_normalized_to_canonical_watch_url(self):
        cases = [
            f"https://www.youtube.com/watch?v={VIDEO_ID}",
            f"https://youtu.be/{VIDEO_ID}?si=share-token",
            f"https://m.youtube.com/watch?v={VIDEO_ID}&feature=share",
            f"https://music.youtube.com/watch?v={VIDEO_ID}&feature=share",
            f"https://www.youtube.com/shorts/{VIDEO_ID}?si=share-token",
            f"https://www.youtube.com/live/{VIDEO_ID}?feature=share",
            f"https://www.youtube.com/embed/{VIDEO_ID}?start=30",
            f"https://www.youtube.com/v/{VIDEO_ID}",
            f"https://www.youtube-nocookie.com/embed/{VIDEO_ID}?rel=0",
            f"youtube.com/watch?v={VIDEO_ID}&list=PL123",
            f"https://www.youtube.com/attribution_link?u=%2Fwatch%3Fv%3D{VIDEO_ID}%26feature%3Dshare",
            f"https://www.youtube.com/redirect?q=https%3A%2F%2Fyoutu.be%2F{VIDEO_ID}%3Fsi%3Dshare-token",
        ]

        for url in cases:
            with self.subTest(url=url):
                self.assertTrue(is_valid_youtube_url(url))
                self.assertEqual(extract_youtube_video_id(url), VIDEO_ID)
                self.assertEqual(normalize_youtube_url(url), CANONICAL_URL)

    def test_clip_urls_are_accepted_without_forced_rewrite(self):
        clip_url = "https://www.youtube.com/clip/Ugkx1234567890abcdefghijklmnopqrstuv"

        self.assertTrue(is_valid_youtube_url(clip_url))
        self.assertIsNone(extract_youtube_video_id(clip_url))
        self.assertEqual(normalize_youtube_url(clip_url), clip_url)

    def test_non_video_or_invalid_urls_are_rejected(self):
        cases = [
            "https://www.youtube.com/playlist?list=PL12345",
            "https://www.youtube.com/@openai",
            "https://www.example.com/watch?v=xi7fgg4-ZhY",
            "https://youtu.be/too-short",
            "",
        ]

        for url in cases:
            with self.subTest(url=url):
                self.assertFalse(is_valid_youtube_url(url))
                self.assertIsNone(extract_youtube_video_id(url))


if __name__ == "__main__":
    unittest.main()
