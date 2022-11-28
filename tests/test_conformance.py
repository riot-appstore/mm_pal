from mm_pal.conformance_test import BaseConformanceSuite
import pytest

class TestMockIf(BaseConformanceSuite):
    @pytest.fixture
    def target(self, mock_app_json, mm_if_inst):
        self.resolved_write_permission = 1
        return mm_if_inst
