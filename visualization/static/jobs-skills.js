const width = window.innerWidth;
const height = window.innerHeight;
const svg = d3.select("#network-svg");

d3.json("/api/graph?min_jaccard=0.0").then(graph => {
  const status = d3.select("#status");

  const links = graph.edges || graph.links || graph;

  if (!links || links.length === 0) {
    status.text("No data returned from API.");
    return;
  }

  // Extract unique nodes from source/target pairs if nodes array isn't provided directly
  let nodes = graph.nodes;
  if (!nodes) {
    const nodeSet = new Set();
    links.forEach(l => {
      nodeSet.add(l.source);
      nodeSet.add(l.target);
    });
    nodes = Array.from(nodeSet).map(id => ({ id }));
  }

  status.text(`Loaded ${nodes.length} skills & ${links.length} connections.`);

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(120))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2));

  const link = svg.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(links)
    .enter().append("line")
    .attr("stroke-width", d => Math.max((d.value || d.weight || 1) * 5, 1.5));

  const node = svg.append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(nodes)
    .enter().append("g");

  node.append("circle").attr("r", 8);
  node.append("text").attr("x", 12).attr("y", 4).text(d => d.id);

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });
}).catch(err => {
  d3.select("#status").text("Error rendering network.");
  console.error(err);
});
