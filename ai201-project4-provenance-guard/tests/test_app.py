import os
import unittest

from app import app
import detector
import store


class ProvenanceGuardAppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def setUp(self):
        for filename in ["audit_log.json", "submissions.json", "appeals.json"]:
            path = os.path.join(os.path.dirname(store.__file__), filename)
            if os.path.exists(path):
                os.remove(path)

    def test_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})

    def test_fallback_signal_produces_multi_signal_result(self):
        result = detector.analyze(
            "Artificial intelligence represents a transformative paradigm shift in modern society. "
            "It is important to note that while the benefits of AI are numerous, it is equally essential to "
            "consider the ethical implications."
        )
        self.assertIsNotNone(result["llm_score"])
        self.assertIsNotNone(result["burstiness_score"])
        self.assertIsNotNone(result["combined_score"])
        self.assertIn(result["attribution"], {"likely_human", "uncertain", "likely_ai"})

    def test_semantic_proxy_is_used_when_groq_is_unavailable(self):
        result = detector.analyze(
            "Artificial intelligence represents a transformative paradigm shift in modern society. "
            "It is important to note that while the benefits of AI are numerous, it is equally essential to "
            "consider the ethical implications."
        )
        self.assertEqual(result["llm_source"], "semantic_proxy")
        self.assertIn("semantic proxy", result["llm_reason"].lower())
        self.assertGreater(result["llm_score"], 0.5)

    def test_submit_and_log(self):
        response = self.client.post(
            "/submit",
            json={"text": "A short human-written paragraph with a bit of personality.", "creator_id": "u1"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("content_id", payload)
        self.assertEqual(payload["status"], "classified")
        self.assertIn("label", payload)

        log_response = self.client.get("/log")
        self.assertEqual(log_response.status_code, 200)
        entries = log_response.get_json()["entries"]
        self.assertTrue(entries)

    def test_stretch_features(self):
        response = self.client.post(
            "/submit",
            json={
                "text": "A short human-written paragraph with a bit of personality.",
                "creator_id": "u3",
                "media": {"type": "image", "source": "upload", "name": "demo.png"},
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertIn("certificate_id", payload)
        self.assertIn("lexical_diversity", payload["signals"])
        self.assertEqual(payload["media"]["type"], "image")

        cert_response = self.client.get(f"/certificate/{payload['content_id']}")
        self.assertEqual(cert_response.status_code, 200)
        certificate = cert_response.get_json()
        self.assertEqual(certificate["content_id"], payload["content_id"])
        self.assertEqual(certificate["attribution"], payload["attribution"])

        analytics_response = self.client.get("/analytics")
        self.assertEqual(analytics_response.status_code, 200)
        analytics = analytics_response.get_json()
        self.assertGreaterEqual(analytics["submissions_total"], 1)
        self.assertGreaterEqual(analytics["appeals_total"], 0)

    def test_appeal_flow(self):
        submit_response = self.client.post(
            "/submit",
            json={"text": "A short human-written paragraph with a bit of personality.", "creator_id": "u2"},
        )
        content_id = submit_response.get_json()["content_id"]

        appeal_response = self.client.post(
            "/appeal",
            json={"content_id": content_id, "creator_reasoning": "I wrote this myself."},
        )
        self.assertEqual(appeal_response.status_code, 200)
        appeal_payload = appeal_response.get_json()
        self.assertEqual(appeal_payload["status"], "under_review")

        appeals_response = self.client.get("/appeals")
        self.assertEqual(appeals_response.status_code, 200)
        self.assertTrue(appeals_response.get_json()["appeals"])


if __name__ == "__main__":
    unittest.main()
