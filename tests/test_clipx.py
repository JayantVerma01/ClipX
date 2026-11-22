"""Unit tests for the pure logic of ClipX. Run:  python -m unittest discover tests -v
(No network, no ffmpeg, no YouTube: everything here is deterministic.)"""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from clipx import framing, lang, moments, qa, rights, signals, tracking, uploader
from clipx.pro import _atempo, timeline


class TimelineTests(unittest.TestCase):
    def test_hard_cut_pieces_overlap_by_one_frame_only(self):
        lens, start, offs, dur = timeline([{"s": 0, "e": 10, "tr": "cut"}, {"s": 0, "e": 5, "tr": "cut"}])
        self.assertEqual(lens, [10.0, 5.0])
        self.assertAlmostEqual(start[1], 10 - 0.05)
        self.assertAlmostEqual(dur, 10 - 0.05 + 5)

    def test_slow_motion_piece_is_longer_than_its_source_range(self):
        lens, _, _, dur = timeline([{"s": 100, "e": 102, "speed": 0.5}])
        self.assertEqual(lens, [4.0])
        self.assertEqual(dur, 4.0)

    def test_atempo_chain_handles_slow_and_fast(self):
        self.assertEqual(_atempo(1.0), "")
        self.assertEqual(_atempo(0.5), ",atempo=0.5000")
        self.assertIn("atempo=0.5,atempo=0.8000", _atempo(0.4))
        self.assertIn("atempo=2.0,atempo=1.5000", _atempo(3.0))


class FramingTests(unittest.TestCase):
    def test_in_game_faces_are_not_webcams(self):
        big_middle = [[(800, 300, 320, 420)] for _ in range(6)]
        self.assertIsNone(framing.pick_facecam(big_middle, 1920, 1080))

    def test_persistent_small_corner_face_is_a_webcam(self):
        samples = [[(1700, 40, 120, 130)] for _ in range(6)]
        cam = framing.pick_facecam(samples, 1920, 1080)
        self.assertIsNotNone(cam)
        self.assertGreater(cam[2], 1800)

    def test_moving_small_face_is_not_a_webcam(self):
        samples = [[(100 + i * 250, 40, 100, 110)] for i in range(6)]
        self.assertIsNone(framing.pick_facecam(samples, 1920, 1080))

    def test_crop_slides_away_from_webcam_on_the_right(self):
        cam = (1500, 0, 1920, 400)
        cx, clear = framing.crop_cx_avoiding(cam, 1920, 1080, crop_w=700, preferred=0.9)
        self.assertTrue(clear)
        self.assertLess(cx * (1920 - 700) + 700, 1500 + 1)
        self.assertEqual(framing.crop_cx_avoiding(None, 1920, 1080, 700, 0.5), (0.5, True))


class ExposureTests(unittest.TestCase):
    def test_dark_footage_is_lifted_and_normal_footage_is_left_alone(self):
        self.assertGreater(framing.lift_gamma(10), 1.5)
        self.assertEqual(framing.lift_gamma(70), 1.0)
        self.assertEqual(framing.lift_gamma(48), 1.0)             # close enough to the target: untouched

    def test_lift_is_capped_and_never_darkens(self):
        self.assertLessEqual(framing.lift_gamma(1), 1.8)
        self.assertGreaterEqual(framing.lift_gamma(30), 1.0)


class QaTests(unittest.TestCase):
    def test_black_white_and_flat_frames_are_counted(self):
        black = np.zeros((4, 9, 16))
        white = np.full((4, 9, 16), 250.0)
        flat = np.full((4, 9, 16), 120.0)
        noisy = np.random.default_rng(0).uniform(0, 255, (8, 9, 16))
        r = qa.classify_frames(np.concatenate([black, white, flat, noisy]), skip_edges=0)
        self.assertAlmostEqual(r["dark"], 4 / 20)
        self.assertAlmostEqual(r["white"], 4 / 20)
        self.assertAlmostEqual(r["flat"], 4 / 20)

    def test_one_frame_flash_is_a_glitch_but_a_hard_cut_is_not(self):
        base = np.full((30, 9, 16), 100.0)
        base += np.random.default_rng(1).normal(0, 0.3, base.shape)
        glitched = base.copy()
        glitched[12] = 220.0
        self.assertEqual(qa.glitch_frames(glitched), [round(12 / 30, 2)])
        cut = base.copy()
        cut[15:] = 30.0
        self.assertEqual(qa.glitch_frames(cut), [])


class RightsTests(unittest.TestCase):
    def test_official_publishers_are_blocked(self):
        self.assertEqual(rights.classify({"channel": "IGN", "title": "GTA 6 Review"})[0], "blocked")
        self.assertEqual(rights.classify({"channel": "Rockstar Games", "title": "Trailer 3"})[0], "blocked")

    def test_creative_commons_is_detected_from_the_licence_field(self):
        meta = {"channel": "Some Creator", "title": "my clip", "license": "Creative Commons Attribution license (reuse allowed)"}
        self.assertEqual(rights.classify(meta)[0], "cc")

    def test_ordinary_creator_is_third_party(self):
        self.assertEqual(rights.classify({"channel": "DubStepZz", "title": "GTA 6 4K"})[0], "third-party")

    def test_gate_blocks_if_any_source_is_blocked_and_warns_for_third_party(self):
        fake = {"a": {"status": "third-party", "reason": "x", "channel": "A"},
                "b": {"status": "blocked", "reason": "y", "channel": "B"},
                "c": {"status": "own", "reason": "z", "channel": "C"}}
        with patch.object(rights, "status_of", side_effect=lambda v: fake[v]):
            self.assertEqual(rights.gate(["c"])[0], "ok")
            self.assertEqual(rights.gate(["a", "c"])[0], "warn")
            self.assertEqual(rights.gate(["a", "b"])[0], "block")


class UploaderTests(unittest.TestCase):
    def test_clean_video_is_clean(self):
        res = {"status": {"uploadStatus": "processed"}, "contentDetails": {}, "processingDetails": {"processingStatus": "succeeded"}}
        self.assertEqual(uploader.assess(res)[0], "clean")

    def test_processing_video_is_pending(self):
        res = {"status": {"uploadStatus": "uploaded"}, "processingDetails": {"processingStatus": "processing"}}
        self.assertEqual(uploader.assess(res)[0], "pending")

    def test_worldwide_block_is_blocked_like_the_first_short(self):
        res = {"status": {"uploadStatus": "processed"}, "contentDetails": {"regionRestriction": {"allowed": []}},
               "processingDetails": {"processingStatus": "succeeded"}}
        self.assertEqual(uploader.assess(res)[0], "blocked")

    def test_some_countries_blocked_is_restricted_not_blocked(self):
        res = {"status": {"uploadStatus": "processed"}, "contentDetails": {"regionRestriction": {"blocked": ["DE", "JP"]}},
               "processingDetails": {"processingStatus": "succeeded"}}
        self.assertEqual(uploader.assess(res)[0], "restricted")

    def test_rejected_upload_is_blocked_with_reason(self):
        res = {"status": {"uploadStatus": "rejected", "rejectionReason": "copyright"}}
        state, why = uploader.assess(res)
        self.assertEqual(state, "blocked")
        self.assertIn("copyright", why)

    def test_ist_time_becomes_utc_for_publish_at(self):
        self.assertEqual(uploader.to_utc_rfc3339("2026-11-21T12:00:00+05:30"), "2026-11-21T06:30:00Z")
        self.assertEqual(uploader.to_utc_rfc3339("2026-11-21T12:00:00"), "2026-11-21T06:30:00Z")   # naive = IST

    def test_same_content_gives_same_fingerprint(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.mp4"), os.path.join(d, "b.mp4")
            for f in (a, b):
                open(f, "wb").write(b"x" * 1000)
            self.assertEqual(uploader.file_sha(a), uploader.file_sha(b))
            open(b, "ab").write(b"y")
            self.assertNotEqual(uploader.file_sha(a), uploader.file_sha(b))


class SignalTests(unittest.TestCase):
    def _burst(self, t0, users, text):
        return [{"t": t0 + i * 0.3, "user": f"u{i}", "text": text} for i in range(users)]

    def test_diverse_reaction_burst_beats_background_chat(self):
        msgs = [{"t": t, "user": f"v{t % 3}", "text": "hello"} for t in range(0, 100, 4)]
        msgs += self._burst(50, 14, "OMG NO WAY")
        arr = signals.score_chat(msgs, 100)
        self.assertGreater(arr[52], arr[10] + 1.0)

    def test_one_spammer_cannot_create_a_burst(self):
        msgs = [{"t": t, "user": f"v{t % 3}", "text": "hello"} for t in range(0, 100, 4)]
        msgs += [{"t": 50 + i * 0.1, "user": "spam", "text": "lol"} for i in range(60)]
        arr = signals.score_chat(msgs, 100)
        self.assertLess(arr[52], 1.5)

    def test_heatmap_only_counts_above_average_spots(self):
        hm = [{"start_time": i * 10, "end_time": i * 10 + 10, "value": 0.3} for i in range(10)]
        hm[4]["value"] = 1.0
        arr = signals.score_heatmap(hm, 100)
        self.assertEqual(arr[5], 0.0)
        self.assertGreater(arr[45], 3.0)

    def test_external_signal_pulls_the_chosen_moment_towards_it(self):
        dur = 400
        energy = np.full(dur, 0.1)
        segs = [{"start": i * 10, "end": i * 10 + 9, "text": "", "words": []} for i in range(dur // 10)]
        plain = moments.find_moments(segs, energy, (40, 90), 1)
        ext = np.zeros(dur)
        ext[300:330] = 4.0
        boosted = moments.find_moments(segs, energy, (40, 90), 1, external=ext)
        self.assertTrue(250 <= boosted[0][1] <= 330, boosted)
        self.assertNotEqual(plain[0][1], boosted[0][1])


class LanguageTests(unittest.TestCase):
    def test_hindi_romanises_to_readable_hinglish(self):
        self.assertEqual(lang.romanize_hindi("क्या"), "kya")
        self.assertEqual(lang.romanize_hindi("घर"), "ghar")
        self.assertEqual(lang.romanize_hindi("यह बहुत मज़ेदार है"), "yah bahut mazedaar hai")

    def test_masking_hits_swears_but_not_innocent_words(self):
        self.assertEqual(lang.mask_word("shit"), "s***")
        self.assertEqual(lang.mask_word("class"), "class")
        self.assertEqual(lang.mask_word("Lucia"), "Lucia")

    def test_hindi_lock_after_three_confident_votes(self):
        lock = lang.LanguageLock()
        for _ in range(2):
            lock.vote("hi", 0.9)
        self.assertIsNone(lock.locked())
        lock.vote("hi", 0.9)
        self.assertEqual(lock.locked(), "hi")

    def test_english_stream_never_locks_and_forced_language_wins(self):
        lock = lang.LanguageLock()
        for _ in range(5):
            lock.vote("en", 0.95)
        lock.vote("hi", 0.9)
        self.assertIsNone(lock.locked())
        self.assertEqual(lang.LanguageLock(forced="hi").locked(), "hi")

    def test_caption_language_rules(self):
        self.assertEqual(lang.caption_language("en", "hello")[0], "English")
        self.assertEqual(lang.caption_language("hi", "kya baat")[0], "Hinglish")
        self.assertEqual(lang.caption_language("es", "hola")[0], "none")


class TrackingTests(unittest.TestCase):
    def test_pick_player_prefers_large_central_person(self):
        people = [(100, 300, 60, 150, .9), (880, 350, 140, 420, .8), (1500, 300, 50, 120, .9)]
        x = tracking.pick_player(people, 1920, 1080)
        self.assertAlmostEqual(x, (880 + 70) / 1920)

    def test_pick_player_ignores_tiny_and_edge_people(self):
        self.assertIsNone(tracking.pick_player([(900, 500, 20, 60, .9), (10, 300, 100, 500, .9)], 1920, 1080))

    def test_pick_player_sticks_to_previous_target(self):
        a, b = (500, 300, 150, 450, .9), (1100, 300, 160, 460, .9)
        x = tracking.pick_player([a, b], 1920, 1080, prev_x=(500 + 75) / 1920)
        self.assertAlmostEqual(x, (500 + 75) / 1920)

    def test_smooth_path_fills_gaps_and_removes_spike(self):
        out = tracking.smooth_path([0, .5, 1, 1.5, 2], [None, .4, .9, .4, .4])
        self.assertEqual(len(out), 5)
        self.assertTrue(all(abs(v - .4) < .1 for v in out))

    def test_smooth_path_limits_speed(self):
        out = tracking.smooth_path([0, 1, 2], [.2, .8, .8], max_speed=.1)
        self.assertLessEqual(max(abs(b - a) for a, b in zip(out, out[1:])), .1 + 1e-9)

    def test_smooth_path_all_missing_uses_default(self):
        self.assertEqual(tracking.smooth_path([0, 1], [None, None], default=.5), [.5, .5])

    def test_left_expr_clamps_and_scales_time_by_speed(self):
        self.assertEqual(tracking.left_expr([(0, 0.0)], 600, 1920), "0.0")
        self.assertEqual(tracking.left_expr([(0, 1.0)], 600, 1920), "1320.0")
        e = tracking.left_expr([(0, .5), (2, .5)], 600, 1920, speed=0.5)
        self.assertIn("lt(t", e)
        self.assertIn("4.00", e)          # key time 2 s at 0.5x speed -> 4 s piece-local


if __name__ == "__main__":
    unittest.main()
