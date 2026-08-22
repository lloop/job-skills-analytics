import json
import unittest
from unittest.mock import MagicMock, patch

from visualization.app import app


class TestVisualizationApp(unittest.TestCase):

    def setUp(self) -> None:
        """Configure the Flask application for testing."""
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_route(self) -> None:
        """Verify the index page renders successfully."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    @patch("visualization.app.DatabaseManager")
    def test_get_graph_api_success(self, mock_db_cls: MagicMock) -> None:
        """Verify /api/graph returns formatted D3 nodes and links."""
        # 1. Setup mock database instance & return value
        mock_db_instance = MagicMock()
        mock_db_cls.return_value.__enter__.return_value = mock_db_instance

        mock_db_instance.get_network_edge_list.return_value = [
            ("python", "docker", 0.5),
            ("python", "aws", 0.3),
        ]

        # 2. Make request to API endpoint
        response = self.client.get("/api/graph?min_jaccard=0.03")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, "application/json")

        # 3. Assert JSON structure
        data = json.loads(response.data)

        expected_nodes = [
            {"id": "aws"},
            {"id": "docker"},
            {"id": "python"},
        ]
        expected_links = [
            {"source": "python", "target": "docker", "value": 0.5},
            {"source": "python", "target": "aws", "value": 0.3},
        ]

        self.assertEqual(data["nodes"], expected_nodes)
        self.assertEqual(data["links"], expected_links)

        # Assert correct min_jaccard was passed into DatabaseManager method
        mock_db_instance.get_network_edge_list.assert_called_once_with(
            min_jaccard=0.03
        )

    @patch("visualization.app.DatabaseManager")
    def test_get_graph_api_empty_data(self, mock_db_cls: MagicMock) -> None:
        """Verify /api/graph handles empty edge lists gracefully."""
        mock_db_instance = MagicMock()
        mock_db_cls.return_value.__enter__.return_value = mock_db_instance
        mock_db_instance.get_network_edge_list.return_value = []

        response = self.client.get("/api/graph?min_jaccard=0.99")
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.data)
        self.assertEqual(data, {"nodes": [], "links": []})


if __name__ == "__main__":
    unittest.main()