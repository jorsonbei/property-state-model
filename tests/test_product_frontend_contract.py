from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "outputs" / "psm_v0" / "product_alpha_app" / "static"


class ProductFrontendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (STATIC / "index.html").read_text(encoding="utf-8")
        cls.javascript = (STATIC / "app.js").read_text(encoding="utf-8")
        cls.css = (STATIC / "styles.css").read_text(encoding="utf-8")

    def test_request_lifecycle_controls_are_accessible(self) -> None:
        for element_id in (
            "request-feedback",
            "request-status",
            "request-elapsed",
            "cancel",
            "retry",
            "evidence-route-status",
            "evidence-route-sources",
            "evidence-route-failures",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        self.assertIn('role="status"', self.html)
        self.assertIn('aria-label="輸入聊天問題"', self.html)
        self.assertIn('aria-controls="debug-panel"', self.html)
        self.assertNotIn('<details class="debug-panel" id="debug-panel" open', self.html)

    def test_cancel_timeout_retry_and_progressive_answer_are_implemented(self) -> None:
        self.assertIn("new AbortController()", self.javascript)
        self.assertIn("REQUEST_TIMEOUT_MS = 70000", self.javascript)
        self.assertIn("controller.abort()", self.javascript)
        self.assertIn("retryLastTurn", self.javascript)
        self.assertIn("discardUnansweredFailedTurn", self.javascript)
        self.assertIn("pushAssistantProgressively", self.javascript)
        self.assertIn("state.lastFailed", self.javascript)
        self.assertIn("payload.route_execution", self.javascript)
        self.assertIn("payload.task_state_graph", self.javascript)
        self.assertIn("status.ready_for_stable_internal_chat", self.javascript)
        self.assertIn("內部聊天 Alpha 總門已通過", self.javascript)
        self.assertIn("task_state_graph: state.taskGraph", self.javascript)
        self.assertIn('id="graph-protocol"', self.html)
        self.assertIn('id="graph-failure-queue"', self.html)

    def test_debug_state_never_enters_main_message_renderer(self) -> None:
        render_start = self.javascript.index("function renderMessages()")
        render_end = self.javascript.index("function messageLabel", render_start)
        renderer = self.javascript[render_start:render_end]
        self.assertNotIn("state_continuity", renderer)
        self.assertNotIn("message system", renderer)
        self.assertNotIn("debug-panel", renderer)

    def test_mobile_layout_has_stable_tracks_and_overflow_controls(self) -> None:
        self.assertIn("grid-template-columns: repeat(3, minmax(0, 1fr))", self.css)
        self.assertIn("overflow-x: auto", self.css)
        self.assertIn("overflow-wrap: anywhere", self.css)
        self.assertIn("@media (max-width: 640px)", self.css)


if __name__ == "__main__":
    unittest.main()
