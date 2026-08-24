const width = window.innerWidth;
const height = window.innerHeight;
const svg = d3.select("#network-svg");

// group that zoom/pan transforms
const g = svg.append("g");

const zoom = d3.zoom()
  .scaleExtent([0.1, 8])
  .on("zoom", (event) => {
    g.attr("transform", event.transform);
  });

svg.call(zoom);

d3.json("/api/graph?min_jaccard=0.0").then(graph => {
  const status = d3.select("#status");
  const links = graph.edges || graph.links || graph;

  if (!links || links.length === 0) {
    status.text("No data returned from API.");
    return;
  }

  let nodes = graph.nodes;
  if (!nodes) {
    const nodeSet = new Set();
    links.forEach(l => {
      nodeSet.add(l.source);
      nodeSet.add(l.target);
    });
    nodes = Array.from(nodeSet).map(id => ({ id }));
  }

  // compute degree (connection count) per node
  const degree = {};
  nodes.forEach(n => degree[n.id] = 0);
  links.forEach(l => {
    const sourceId = l.source.id || l.source;
    const targetId = l.target.id || l.target;
    degree[sourceId] = (degree[sourceId] || 0) + 1;
    degree[targetId] = (degree[targetId] || 0) + 1;
  });
  nodes.forEach(n => n.degree = degree[n.id] || 0);

  // scale degree to a radius range
  const radiusScale = d3.scaleSqrt()
    .domain([0, d3.max(nodes, d => d.degree) || 1])
    .range([5, 30]);

  status.text(`Loaded ${nodes.length} skills & ${links.length} connections.`);

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id(d => d.id).distance(120))
    .force("charge", d3.forceManyBody().strength(-300))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide(d => radiusScale(d.degree) + 2));

  const link = g.append("g")
    .attr("class", "links")
    .selectAll("line")
    .data(links)
    .enter().append("line")
    .attr("stroke-width", d => Math.max((d.value || d.weight || 1) * 5, 1.5));

  const node = g.append("g")
    .attr("class", "nodes")
    .selectAll("g")
    .data(nodes)
    .enter().append("g")
    .call(drag(simulation));

  node.append("circle")
    .attr("r", d => radiusScale(d.degree));

  node.append("text")
    .attr("x", d => radiusScale(d.degree) + 4)
    .attr("y", 4)
    .text(d => d.id);

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

function drag(simulation) {
  function dragstarted(event, d) {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragged(event, d) {
    d.fx = event.x;
    d.fy = event.y;
  }
  function dragended(event, d) {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}