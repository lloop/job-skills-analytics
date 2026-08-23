import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from visualization.d3_exporter import export_d3_network


class TestD3Exporter(unittest.TestCase):

    def setUp(self) -> None:
        """Create a temporary directory for output file assertions."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_dir = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    @patch("visualization.d3_exporter.DatabaseManager")
    def test_export_d3_network_success(self, mock_db_cls: MagicMock) -> None:
        """Verify graph nodes/links are formatted and output files are created."""
        # 1. Setup mock database return values
        mock_db_instance = MagicMock()
        mock_db_cls.return_value.__enter__.return_value = mock_db_instance

        # Return sample edge list: (source, target, weight)
        mock_db_instance.get_network_edge_list.return_value = [
            ("python", "docker", 0.5),
            ("python", "aws", 0.3),
        ]

        # 2. Execute export
        export_d3_network(
            db_path=":memory:",
            output_dir=self.output_dir,
            min_jaccard=0.03,
        )

        # 3. Assert JSON file contents
        json_file = self.output_dir / "skills_graph.json"
        self.assertTrue(json_file.exists())

        data = json.loads(json_file.read_text())
        
        # Unique nodes should be sorted: aws, docker, python
        expected_nodes = [
            {"id": "aws", "group": 1},
            {"id": "docker", "group": 1},
            {"id": "python", "group": 1},
        ]
        expected_links = [
            {"source": "python", "target": "docker", "value": 0.5},
            {"source": "python", "target": "aws", "value": 0.3},
        ]

        self.assertEqual(data["nodes"], expected_nodes)
        self.assertEqual(data["links"], expected_links)

        # 4. Assert HTML template was copied if source template exists
        template_file = self.output_dir / "network.html"
        source_template = (
            Path(__file__).parents[1]
            / "visualization"
            / "templates"
            / "network.html"
        )
        if source_template.exists():
            self.assertTrue(template_file.exists())

    @patch("visualization.d3_exporter.DatabaseManager")
    def test_export_d3_network_no_edges(self, mock_db_cls: MagicMock) -> None:
        """Verify no files are written when no edge data meets the threshold."""
        mock_db_instance = MagicMock()
        mock_db_cls.return_value.__enter__.return_value = mock_db_instance
        mock_db_instance.get_network_edge_list.return_value = []

        export_d3_network(
            db_path=":memory:",
            output_dir=self.output_dir,
            min_jaccard=0.5,
        )

        json_file = self.output_dir / "skills_graph.json"
        self.assertFalse(json_file.exists())


if __name__ == "__main__":
    unittest.main()