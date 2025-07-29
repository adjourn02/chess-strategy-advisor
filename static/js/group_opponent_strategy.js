// set up the dimensions of the chart
var margin = { top: 70, right: 140, bottom: 60, left: 220};
var width = 700 - margin.left - margin.right;
var height = 600 - margin.top - margin.bottom;

// SVG containers for both charts
var white_strategy_svg = d3.select('#white_strategy').append('svg')
              .attr('width', width + margin.left + margin.right)
              .attr('height', height + margin.top + margin.bottom)
              .append("g")
              .attr('transform', `translate(${margin.left},${margin.top})`);

var black_strategy_svg = d3.select('#black_strategy').append('svg')
              .attr('width', width + margin.left + margin.right)
              .attr('height', height + margin.top + margin.bottom)
              .append("g")
              .attr('transform', `translate(${margin.left},${margin.top})`);

d3.json('/strategy').then(function (data) {

    // remove loading
    d3.select("#load3").remove();
    d3.select("#load4").remove();

    let top25_strategy = data["top25_agg_strategy"];
    let rec_black = top25_strategy["recommended_black"];
    let rec_white = top25_strategy["recommended_white"];

    // sort the datasets
    rec_black.sort((a, b) => b.difference - a.difference);
    rec_white.sort((a, b) => b.difference - a.difference);

    var initialXDomain_black = [Math.min(0, d3.min(rec_black, d => d.difference)),
            Math.max(0, d3.max(rec_black, d => d.difference))];
    var initialXDomain_white = [Math.min(0, d3.min(rec_white, d => d.difference)),
            Math.max(0, d3.max(rec_white, d => d.difference))];

    // define scales
    const x = d3.scaleLinear().range([0, width]);
    const y = d3.scaleBand().range([height, 0]).padding(0.1);

    // define axes
    const xAxis = d3.axisBottom(x).ticks(5);
    const yAxis = d3.axisLeft(y).tickPadding(10).tickSize(0);

    white_strategy_svg.append("text")
        .attr("x", margin.left - 270)
        .attr("y", margin.top - 90)
        .style("font-size", "24px")
        .style("font-weight", "bolder")
        .style("font-family", "sans-serif")
        .text("Strategy when playing White");

    black_strategy_svg.append("text")
        .attr("x", margin.left - 270)
        .attr("y", margin.top - 90)
        .style("font-size", "24px")
        .style("font-weight", "bolder")
        .style("font-family", "sans-serif")
        .text("Strategy when playing Black");

    // render initial charts
    renderChart(rec_white, white_strategy_svg, true);
    renderChart(rec_black, black_strategy_svg, false);

    // dropdown change event listener-----------------------------------------------------------------------------------

     d3.select('#elo_dropdown').on('change', function() {
      updateWhiteChart(data, white_strategy_svg);
      updateBlackChart(data, black_strategy_svg);
     });

     d3.select('#filter_dropdown').on('change', function() {
      updateWhiteChart(data, white_strategy_svg);
      updateBlackChart(data, black_strategy_svg);
     });

     // update strategies when playing white
    function updateWhiteChart(data, svg) {
        var no_of_opp = d3.select('#elo_dropdown').property('value');
        var subset_data
        var white_data

        // filter players
        if (no_of_opp === "top10") {
            subset_data = data['top10_agg_strategy']
            white_data = subset_data['recommended_white']
        } else if (no_of_opp === "bot10") {
            subset_data = data['bot10_agg_strategy']
            white_data = subset_data['recommended_white']
        } else {
            subset_data = data['top25_agg_strategy'];
            white_data = subset_data['recommended_white']
        }

        // define domain based on all confidences
        initialXDomain_white = [Math.min(0, d3.min(white_data, d => d.difference)),
            Math.max(0, d3.max(white_data, d => d.difference))];

        // filter confidence
        const topValues = +d3.select('#filter_dropdown').property('value');
        let filteredData;
        if (topValues == 0.7) {
            filteredData = white_data.filter(p => p.confidence >= 0.7);
        } else if (topValues == 0.9) {
            filteredData = white_data.filter(p => p.confidence >= 0.9);
        }else {
            filteredData = white_data;
        }

        renderChart(filteredData, svg, true);
    }

    // update strategies when playing black
    function updateBlackChart(data, svg) {
        var no_of_opp = d3.select('#elo_dropdown').property('value');
        var subset_data
        var black_data

        // filter players
        if (no_of_opp === "top10") {
            subset_data = data['top10_agg_strategy'];
            black_data = subset_data['recommended_black']
        } else if (no_of_opp === "bot10") {
            subset_data = data['bot10_agg_strategy'];
            black_data = subset_data['recommended_black']
        } else {
            subset_data = data['top25_agg_strategy'];
            black_data = subset_data['recommended_black']
        }

        // define domain based on all confidences
        initialXDomain_black = [Math.min(0, d3.min(black_data, d => d.difference)),
            Math.max(0, d3.max(black_data, d => d.difference))];

        // filter confidence
        const topValues = +d3.select('#filter_dropdown').property('value');
        let filteredData;
        if (topValues == 0.7) {
            filteredData = black_data.filter(p => p.confidence >= 0.7);
        } else if (topValues == 0.9) {
            filteredData = black_data.filter(p => p.confidence >= 0.9);
        }else {
            filteredData = black_data;
        }

        renderChart(filteredData, svg, false);
    }

    function renderChart(data, svg, opening_color) {

        // update x and y domains
        if(opening_color) {
            x.domain(initialXDomain_white)
        } else {
            x.domain(initialXDomain_black)
        }
        y.domain(data.map(d => d.opening));

        // positive bars
        const positive_data = data.filter(function(d){ return d.difference >= 0 })
        const positiveColorScale = d3.scaleQuantile()
            .range(["#bdd7e7","#6baed6","#3182bd","#08519c"])
            .domain(d3.extent(positive_data.map(function(d) { return d.confidence; })));

        // negative bars
        const negative_data = data.filter(function(d){ return d.difference < 0})
        const negativeColorScale = d3.scaleQuantile()
            .range(["#fcae91","#fb6a4a","#de2d26","#a50f15"])
            .domain(d3.extent(negative_data.map(function(d) { return d.confidence; })));

        // bind data to bars
        const bars = svg.selectAll('.bar').data(data, d => d.opening);

        // remove old bars
        bars.exit().remove();

        // update existing bars
        bars.attr('y', d => y(d.opening))
            .attr('x', d => d.difference >= 0 ? x(0) : x(d.difference))
            .attr('height', y.bandwidth())
            .attr('width', d => d.difference > 0 ? x(d.difference) - x(0) : x(0) - x(d.difference))
            .attr('fill', d => d.difference >= 0
            ? positiveColorScale(d.confidence)  // Apply positive color scale
            : negativeColorScale(d.confidence))

        // add new bars
        bars.enter().append('rect')
            .attr('class', 'bar')
            .attr('y', d => y(d.opening))
            .attr('x', d => d.difference >= 0 ? x(0) : x(d.difference))
            .attr('height', y.bandwidth())
            .attr('width', d => d.difference > 0 ? x(d.difference) - x(0) : x(0) - x(d.difference))
            .attr('fill', d => d.difference >= 0
            ? positiveColorScale(d.confidence)  // Apply positive color scale
            : negativeColorScale(d.confidence))

        // bind data to labels
        var labels = svg.selectAll(".label").data(data, d => d.opening);

        // remove old labels
        labels.exit().transition().duration(200).remove();

        // update existing labels
        labels.transition().duration(200)
            .attr('y', d => y(d.opening) + y.bandwidth() / 2 + 5)  // Center text vertically in the bar
        .attr('x', d => {
        let xPos = d.difference >= 0
              ? x(d.difference) + 10
              : x(0) + 10
        return xPos;
         })
        .attr('text-anchor', 'start')  // Center text horizontally
        .attr('fill', 'black')  // Set the text color to white for visibility
        .attr('font-size', '12px')  // Set font size (adjust as needed)
        .text(d => d.confidence.toFixed(2))
        .style("font-family", "sans-serif");

        labels.enter().append('text')
            .attr('class', 'label')
            .attr('y', d => y(d.opening) + y.bandwidth() / 2 + 5)  // Center text vertically in the bar
            .attr('x', d => {
            let xPos = d.difference >= 0
              ? x(d.difference) + 20
              : x(0) + 20
            return xPos;
             })
            .attr('text-anchor', 'middle')  // Center text horizontally
            .attr('fill', 'black')  // Set the text color to white for visibility
            .attr('font-size', '12px')  // Set font size (adjust as needed)
            .text(d => d.confidence.toFixed(2))
            .style("font-family", "sans-serif");

        // update x-axis
        if (svg.select('.x-axis').empty()) {
        svg.append('g')
            .attr('class', 'x-axis')
            .attr('transform', `translate(0,${height})`);
        }

        svg.select('.x-axis')
            .transition().duration(500)
            .call(xAxis)
            .selectAll("text")
            .style("font-size", "12px")

        // update y-axis
        if (svg.select('.y-axis').empty()) {
            svg.append('g')
                .attr('class', 'y-axis');
        }
        svg.select('.y-axis')
            .transition().duration(500)
            .call(yAxis)
            .selectAll("text")
               .style("font-size", "12px")
               .style("font-family", "sans-serif")

        svg.select('.y-axis').select('path')
            .attr('stroke', 'none')

        // x-axis title
        svg.append("text")
            .attr("class", "axis-title")
            .attr("x", width / 2 - margin.right + 80)
            .attr("y", height + margin.bottom - 20)
            .style("font-weight", "bold")
            .style("font-size", "20px")
            .style("font-family", "sans-serif")
            .text("Differences");

        // update legend for negative bars
        const bins_neg = negativeColorScale.domain(d3.extent(negative_data.map(function(d) { return d.confidence; }))).quantiles()
        const rateMin_neg = Math.min.apply(Math, negative_data.map(function(d) { return d.confidence; }))
        const rateMax_neg = Math.max.apply(Math, negative_data.map(function(d) { return d.confidence; }))
        let keys_neg = ["N/A", "N/A ", "N/A  ", "N/A    "]
        if(Number.isFinite(rateMin_neg) && [...new Set(negative_data.map(d => d.confidence.toFixed(2)))].length > 1) {
            keys_neg = ["[" + String(d3.format(".2f")(rateMin_neg)) + "," + String(d3.format(".2f")(bins_neg[0])) + "]",
                "(" + String(d3.format(".2f")(bins_neg[0])) + "," + String(d3.format(".2f")(bins_neg[1])) + "]",
                "(" + String(d3.format(".2f")(bins_neg[1])) + "," + String(d3.format(".2f")(bins_neg[2])) + "]",
                "(" + String(d3.format(".2f")(bins_neg[2])) + "," + String(d3.format(".2f")(rateMax_neg)) + "]"]
            if(keys_neg[1] == keys_neg[2]) {
                keys_neg = [String(d3.format(".2f")(rateMin_neg)), "N/A", "N/A ", String(d3.format(".2f")(rateMax_neg))]
            }
        } else if(Number.isFinite(rateMin_neg) && [...new Set(negative_data.map(d => d.confidence.toFixed(2)))].length == 1) {
            keys_neg = ["N/A", "N/A ", "N/A  ", String(d3.format(".2f")(rateMax_neg))]
        }

        // update legend for positive bars
        const bins_pos = negativeColorScale.domain(d3.extent(positive_data.map(function(d) { return d.confidence; }))).quantiles()
        const rateMin_pos = Math.min.apply(Math, positive_data.map(function(d) { return d.confidence; }))
        const rateMax_pos = Math.max.apply(Math, positive_data.map(function(d) { return d.confidence; }))
        let keys_pos = ["N/A", "N/A ", "N/A  ", "N/A   "]
        if(Number.isFinite(rateMin_pos) && [...new Set(positive_data.map(d => d.confidence.toFixed(2)))].length > 1) {
            keys_pos = ["[" + String(d3.format(".2f")(rateMin_pos)) + "," + String(d3.format(".2f")(bins_pos[0])) + "]",
                "(" + String(d3.format(".2f")(bins_pos[0])) + "," + String(d3.format(".2f")(bins_pos[1])) + "]",
                "(" + String(d3.format(".2f")(bins_pos[1])) + "," + String(d3.format(".2f")(bins_pos[2])) + "]",
                "(" + String(d3.format(".2f")(bins_pos[2])) + "," + String(d3.format(".2f")(rateMax_pos)) + "]"]
            if(keys_pos[1] == keys_pos[2]) {
                keys_pos = [String(d3.format(".2f")(rateMin_pos)), "N/A", "N/A ", String(d3.format(".2f")(rateMax_pos))]
            }
        } else if(Number.isFinite(rateMin_pos) && [...new Set(positive_data.map(d => d.confidence.toFixed(2)))].length == 1) {
            keys_pos = ["N/A", "N/A ", "N/A  ", String(d3.format(".2f")(rateMax_pos))]
        }

        const size = 12;
        // determine the position of the legend dynamically
        const legendPadding = 20;
        const legendWidth = 150;
        const legendHeight = keys_neg.length * (size + 5);

        // calculate the ideal position for the legend
        let legendX = width - legendWidth - legendPadding;
        let legendY = height < 300 ? legendPadding : height - legendHeight - legendPadding;

        // if the legend overlaps the x-axis, adjust its position
        if (legendY + legendHeight > height) {
            legendY = height - legendHeight - legendPadding;
        }

        svg.select("#legend_neg").remove();

        // set up the negative legend
        const legend_neg = svg.append("g")
            .attr("id", "legend_neg")
            .attr("transform", `translate(${legendX}, ${legendY})`);

        legend_neg.append("text")
            .attr("class", "legend-title")
            .attr("x", 225)
            .attr("y", (d, i) => i * (size + 5) - 370)
            .style("font-weight", "bold")
            .style("font-size", "14px")
            .text("Confidence")
            .style("font-family", "sans-serif");

        svg.select("#legend_pos").remove();

        // set up the positive legend
        const legend_pos = svg.append("g")
            .attr("id", "legend_pos")
            .attr("transform", `translate(${legendX}, ${legendY})`);

        // define color scale for the legend
        const color_neg = d3.scaleOrdinal()
            .range(negativeColorScale.range())
            .domain(keys_neg);

        const color_pos = d3.scaleOrdinal()
            .range(positiveColorScale.range())
            .domain(keys_pos);

        // create legend squares
        legend_neg.selectAll("legend_neg-rects")
            .data(keys_neg)
            .enter()
            .append("rect")
            .attr("x", 225)
            .attr("y", (d, i) => i * (size + 5) - 365)
            .attr("width", size)
            .attr("height", size)
            .style("fill", d => color_neg(d));

        legend_pos.selectAll("legend_pos-rects")
            .data(keys_pos)
            .enter()
            .append("rect")
            .attr("x", 225)
            .attr("y", (d, i) => i * (size + 5) - 295)
            .attr("width", size)
            .attr("height", size)
            .style("fill", d => color_pos(d));

        // create legend labels
        legend_neg.selectAll("legend_neg-texts")
            .data(keys_neg)
            .enter()
            .append("text")
            .attr("x", 225 + size + 5)
            .attr("y", (d, i) => i * (size + 5) - 365 + size / 2)
            .attr("dy", "0.35em")
            .style("font-size", "12px")
            .style("font-family", "sans-serif")
            .text(d => d);

        legend_pos.selectAll("legend_pos-texts")
            .data(keys_pos)
            .enter()
            .append("text")
            .attr("x", 225 + size + 5)
            .attr("y", (d, i) => i * (size + 5) - 295 + size / 2)
            .attr("dy", "0.35em")
            .style("font-size", "12px")
            .style("font-family", "sans-serif")
            .text(d => d);

        // add or update a vertical line along the origin (x = 0)
        const originLine = svg.selectAll('.origin-line').data([0]);

        // update the existing line
        originLine.attr('x1', x(0))
            .attr('x2', x(0))
            .attr('y1', 0)
            .attr('y2', height)
            .attr('stroke', 'black')
            .attr('stroke-width', 1)

        // enter selection: append the line if it does not exist
        originLine.enter().append('line')
            .attr('class', 'origin-line')
            .attr('x1', x(0))
            .attr('x2', x(0))
            .attr('y1', 0)
            .attr('y2', height)
            .attr('stroke', 'black')
            .attr('stroke-width', 1)

        // bring axes to the front
        svg.select('.x-axis').raise();
        svg.select('.y-axis').raise();
        svg.select('.origin-line').raise();
    }
});
