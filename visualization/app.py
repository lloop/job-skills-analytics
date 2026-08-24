"""Flask application serving interactive skill network visualization."""

from pathlib import Path

from flask import Flask, jsonify, render_template, request

from config import DATABASE_PATH, SITE_CONFIGS
from database.db_manager import DatabaseManager

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
)


@app.route("/")
def index():
    site_config = SITE_CONFIGS["remoteok"]
    # print(site_config)
    listing_page = site_config.listing_url

    title = "Welcome to My Flask App!"
    greeting = "Hello, World!"
    return render_template("index.html", title=title, greeting=greeting, listing_page=listing_page)
    # return render_template("index.html")


@app.route("/api/graph")
def get_graph_data():
    """API endpoint delivering D3-formatted nodes and links."""
    min_jaccard = float(request.args.get("min_jaccard", 0.03))
    
    with DatabaseManager(DATABASE_PATH) as db:
        edges = db.get_network_edge_list(min_jaccard=min_jaccard)

    if not edges:
        return jsonify({"nodes": [], "links": []})

    # Collect unique nodes and formatted links
    node_set = {skill for source, target, _ in edges for skill in (source, target)}
    nodes = [{"id": skill} for skill in sorted(node_set)]
    links = [
        {"source": source, "target": target, "value": weight}
        for source, target, weight in edges
    ]

    return jsonify({"nodes": nodes, "links": links})


if __name__ == "__main__":
    app.run(debug=True, port=5000)