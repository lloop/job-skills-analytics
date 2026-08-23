const width = window.innerWidth;
const height = window.innerHeight;
const svg = d3.select("#network-svg");
const tooltip = d3.select("#tooltip");

const g = svg.append("g");

const zoom = d3.zoom()
  .scaleExtent([0.2, 5])
  .on("zoom", (event) => g.attr("transform", event.transform));
svg.call(zoom);

let simulation, linkGroup, nodeGroup;
let currentJaccard = 0.0;
let currentSpacing = 250;

function renderGraph() {
  d3.json(`/api/graph?min_jaccard=${currentJaccard}`).then(data => {
    const status = d3.select("#status");
    const links = data.edges || data.links || [];

    if (!links || links.length === 0) {
      g.selectAll("*").remove();
      status.text("No connections at this threshold.");
      return;
    }

    const degreeMap = {};
    links.forEach(l => {
      degreeMap[l.source] = (degreeMap[l.source] || 0) + 1;
      degreeMap[l.target] = (degreeMap[l.target] || 0) + 1;
    });

    const nodes = Object.keys(degreeMap).map(id => ({
      id,
      degree: degreeMap[id]
    }));

    status.text(`${nodes.length} skills | ${links.length} relationships`);

    g.selectAll("*").remove();

    const chargeStrength = -currentSpacing;
    const linkDistance = Math.min(100 + (currentSpacing * 0.2), 300);

    simulation = d3.forceSimulation(nodes)
      .force("link", d3.forceLink(links).id(d => d.id).distance(linkDistance))
      .force("charge", d3.forceManyBody().strength(chargeStrength))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(d => Math.sqrt(d.degree) * 6 + 12));

    linkGroup = g.append("g")
      .attr("class", "links")
      .selectAll("line")
      .data(links)
      .enter().append("line")
      .attr("stroke-width", d => Math.max((d.value || d.weight || 1) * 8, 1));

    nodeGroup = g.append("g")
      .attr("class", "nodes")
      .selectAll("g")
      .data(nodes)
      .enter().append("g")
      .call(drag(simulation));

    nodeGroup.append("circle")
      .attr("r", d => Math.sqrt(d.degree) * 5 + 4)
      .on("mouseover", (event, d) => {
        tooltip.style("visibility", "visible")
               .html(`<strong>${d.id}</strong><br/>Connections: ${d.degree}`);
      })
      .on("mousemove", (event) => {
        tooltip.style("top", (event.pageY - 10) + "px")
               .style("left", (event.pageX + 15) + "px");
      })
      .on("mouseout", () => tooltip.style("visibility", "hidden"));

    nodeGroup.append("text")
      .attr("x", d => Math.sqrt(d.degree) * 5 + 8)
      .attr("y", 4)
      .text(d => d.id);

    simulation.on("tick", () => {
      linkGroup
        .attr("x1", d => d.source.x)
        .attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x)
        .attr("y2", d => d.target.y);

      nodeGroup.attr("transform", d => `translate(${d.x},${d.y})`);
    });
  });
}

function drag(sim) {
  function dragstarted(event) {
    if (!event.active) sim.alphaTarget(0.3).restart();
    event.subject.fx = event.subject.x;
    event.subject.fy = event.subject.y;
  }

  function dragged(event) {
    event.subject.fx = event.x;
    event.subject.fy = event.y;
  }

  function dragended(event) {
    if (!event.active) sim.alphaTarget(0);
    event.subject.fx = null;
    event.subject.fy = null;
  }

  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
}

renderGraph();

d3.select("#jaccard-slider").on("input", function() {
  currentJaccard = parseFloat(this.value).toFixed(2);
  d3.select("#jaccard-val").text(currentJaccard);
  renderGraph();
});

d3.select("#spacing-slider").on("input", function() {
  currentSpacing = parseInt(this.value, 10);
  d3.select("#spacing-val").text(currentSpacing);
  
  if (simulation) {
    const chargeStrength = -currentSpacing;
    const linkDistance = Math.min(100 + (currentSpacing * 0.2), 300);
    
    simulation.force("charge").strength(chargeStrength);
    simulation.force("link").distance(linkDistance);
    simulation.alpha(0.3).restart();
  }
});