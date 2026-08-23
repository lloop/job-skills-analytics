"""Export skill network graph data to D3.js JSON and serve visualization templates."""

import json
import shutil
from pathlib import Path

from config import DATABASE_PATH
from database.db_manager import DatabaseManager


def export_d3_network(
    db_path: str | Path = DATABASE_PATH,
    output_dir: str | Path = "output",
    min_jaccard: float = 0.03,
) -> None:
    """Export graph nodes/links as JSON and copy the D3 template to output directory."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    with DatabaseManager(db_path) as db:
        edges = db.get_network_edge_list(min_jaccard=min_jaccard)

    if not edges:
        print(f"[WARNING] No skill pairs found above Jaccard threshold >= {min_jaccard}")
        return

    # Build unique nodes and links for D3
    node_set = {skill for source, target, _ in edges for skill in (source, target)}
    nodes = [{"id": skill, "group": 1} for skill in sorted(node_set)]
    links = [
        {"source": source, "target": target, "value": weight}
        for source, target, weight in edges
    ]

    # Save JSON file
    json_path = out_dir / "skills_graph.json"
    json_path.write_text(json.dumps({"nodes": nodes, "links": links}, indent=2))
    print(f"Exported graph data: {json_path.resolve()}")

    # Copy HTML template and its static assets from visualization/
    template_src = Path(__file__).parent / "templates" / "network.html"
    if template_src.exists():
        template_dest = out_dir / "network.html"
        shutil.copy(template_src, template_dest)
        shutil.copytree(
            Path(__file__).parent / "static", out_dir / "static", dirs_exist_ok=True
        )
        print(f"Copied visualization template: {template_dest.resolve()}")


if __name__ == "__main__":
    export_d3_network()