import unittest
from unittest.mock import MagicMock

from ai_coordination_engine.main import AICoordinationEngine


class TestPartitionKeyAssembly(unittest.TestCase):
    def setUp(self):
        self.logger = MagicMock()
        self.setting = {
            "endpoint_id": "test_endpoint",
            "part_id": "test_part",
            "aws_access_key_id": "test_key",
            "aws_secret_access_key": "test_secret",
            "region_name": "us-east-1",
        }

    def test_partition_key_assembly_defaults(self):
        """Test that partition_key is assembled from settings defaults."""
        engine = AICoordinationEngine(self.logger, **self.setting)
        params = {}

        # Access the private method for testing purposes
        engine._apply_partition_defaults(params)

        self.assertEqual(params.get("context", {}).get("endpoint_id"), "test_endpoint")
        self.assertEqual(params.get("context", {}).get("part_id"), "test_part")
        self.assertEqual(params.get("context", {}).get("partition_key"), "test_endpoint#test_part")

    def test_partition_key_assembly_override(self):
        """Test that params override settings for partition_key assembly."""
        engine = AICoordinationEngine(self.logger, **self.setting)
        params = {"endpoint_id": "custom_endpoint", "part_id": "custom_part"}

        engine._apply_partition_defaults(params)

        self.assertEqual(params.get("endpoint_id"), "custom_endpoint")
        self.assertEqual(params.get("part_id"), "custom_part")
        self.assertEqual(params.get("context", {}).get("partition_key"), "custom_endpoint#custom_part")

    def test_partition_key_assembly_mixed(self):
        """Test mixed params and settings."""
        engine = AICoordinationEngine(self.logger, **self.setting)
        params = {"part_id": "new_part"}

        engine._apply_partition_defaults(params)

        self.assertEqual(params.get("context", {}).get("endpoint_id"), "test_endpoint")
        self.assertEqual(params.get("part_id"), "new_part")
        self.assertEqual(params.get("context", {}).get("partition_key"), "test_endpoint#new_part")


if __name__ == "__main__":
    unittest.main()
