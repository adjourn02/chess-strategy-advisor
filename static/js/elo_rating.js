// Set up the dimensions of the chart
const margin_elo = { top: 70, right: 40, bottom: 60, left: 220};
const width_elo = 700 - margin_elo.left - margin_elo.right;
const height_elo = 600 - margin_elo.top - margin_elo.bottom;

// Set up SVG container for the bar chart
const svg = d3.select("#elochart").append("svg")
    .attr("width", width_elo + margin_elo.left + margin_elo.right)
    .attr("height", height_elo + margin_elo.top + margin_elo.bottom)
    .append("g")
    .attr("transform", "translate(150," + margin_elo.top + ")");

// Set up SVG container for the line chart
const svgGameLength = d3.select("#gameLenChart")
    .append("svg")
    .attr("width", width_elo + margin_elo.left + margin_elo.right)
    .attr("height", height_elo + margin_elo.top + margin_elo.bottom)
    .append("g")
    .attr("transform", `translate(120, ${margin_elo.top})`);

// D3 tooltip
tip = d3.tip().attr('id', 'tooltip1').html(function(d) {
    return '<div id="tooltip1-info">Username: ' + d["username"] + '</div>'
                + '<hr id="tooltip1-info" style="border: dashed 2px;">'
                + '<div id="tooltip1-info">Rating Deviation: ' + d["rd"] + '</div>'
                + '<div id="tooltip1-info">Win: ' + d["win"] + '</div>'
                + '<div id="tooltip1-info">Loss: ' + d["loss"] + '</div>'
                + '<div id="tooltip1-info">Draw: ' + d["draw"] + '</div>'
                + '<hr id="tooltip1-info" style="border: 1px solid #ffc469;">'
                + '<div id="tooltip1-info">Move Analysis: '+ '</div>'
                + '<li id="tooltip1-info"><span>Against Castling: '+ d["move_analysis"]["Against Castling"] + '</span></li>'
                + '<li id="tooltip1-info"><span>Against En Passant: '+ d["move_analysis"]["Against En Passant"] + '</span></li>'
                + '<li id="tooltip1-info"><span>Using Castling: '+ d["move_analysis"]["Using Castling"] + '</span></li>'
                + '<li id="tooltip1-info"><span>Using En Passant: '+ d["move_analysis"]["Using En Passant"] + '</span></li>'
})

d3.json('/data').then(function (data) {

    // remove loading
    d3.select("#load1").remove();
    d3.select("#load2").remove();

    // tooltip
    svg.call(tip)

    // sort players
    let opp = data["opponents"];
    opp.sort((a, b) => a.rating - b.rating);
    opp = opp.slice(-25);

    // define axes
    const x = d3.scaleLinear()
        .range([0, width_elo])
        .domain([0, d3.max(opp, d => d.rating)]);

    const y = d3.scaleBand()
        .range([height_elo, 0])
        .padding(0.1)
        .domain(opp.map(d => d.username));

    // create the x and y axes
    const xAxis = d3.axisBottom(x).ticks(5);//.tickSize(0);
    const yAxis = d3.axisLeft(y).tickSize(0).tickPadding(10);

    // draw bars and labels initially
    updateBarChart(opp);

    // add axes
    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height_elo + ")")
        .call(xAxis)
           .selectAll("text")
           .style("font-size", "12px")
        .call(g => g.select(".domain"))

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .selectAll("text")
           .style("font-size", "12px")
           .style("font-family", "sans-serif");

    // chart title
    svg.append("text")
        .attr("x", margin_elo.left - 90)
        .attr("y", margin_elo.top - 90)
        .style("font-size", "24px")
        .style("font-weight", "bold")
        .style("font-family", "sans-serif")
        .text("Elo Ratings");

    // line chart--------------------------------------------------------------------------------------------------------

    const gameLengthData = data["all_smoothed_values"];

    // define scales for x and y axes
    const xScale = d3.scaleLinear()
    .domain(d3.extent(gameLengthData, d => d[0])) // Move count range
    .range([0, width_elo]);
    const yScale = d3.scaleLinear()
        .domain([0,1])
        .range([height_elo, 0]);

    // define line generator function
    const lineGenerator = d3.line()
        .x(d => xScale(d[0])) // x-coordinate based on move count
        .y(d => yScale(d[1])); // y-coordinate based on average score

    // add the line path to the chart (initially empty)
    const linePath = svgGameLength.append("path")
        .datum(gameLengthData)
        .attr("class", "line")
        .attr("d", lineGenerator)
        .attr("fill", "none")
        .attr("stroke", "#cc1d1d")
        .attr("stroke-width", 2);

    const linePath2 = svgGameLength.append("path")
        .datum(data['player_smoothed_values'])
        .attr("class", "line")
        .attr("d", lineGenerator)
        .attr("fill", "none")
        .attr("stroke", "#0356fc")
        .attr("stroke-width", 2);

    // add x-axis to the chart with a class
    const xAxisLine = svgGameLength.append("g")
        .attr("class", "x-axis")
        .attr("transform", `translate(0, ${height_elo})`)
        .call(d3.axisBottom(xScale))
        .selectAll("text")
           .style("font-size", "12px")

    // add y-axis to the chart with a class
    const yAxisLine = svgGameLength.append("g")
        .attr("class", "y-axis")
        .call(d3.axisLeft(yScale))
        .selectAll("text")
           .style("font-size", "12px")

    // add x-axis label
    svgGameLength.append("text")
        .attr("class", "axis-label")
        .attr("x", width_elo / 2 - 50)
        .attr("y", height_elo + 40)
        .attr("fill", "black")
        .style("font-size", "20px")
        .style("font-family", "sans-serif")
        .style("font-weight", "bold")
        .text("Move Count");

    // Add y-axis label
    svgGameLength.append("text")
        .attr("class", "axis-label")
        .attr("x", -height_elo / 2 - 60)
        .attr("y", -40)
        .attr("transform", "rotate(-90)")
        .attr("fill", "black")
        .style("font-size", "20px")
        .style("font-family", "sans-serif")
        .style("font-weight", "bold")
        .text("Average Score");

    // add title to the chart
    svgGameLength.append("text")
        .attr("x", margin_elo.left - 130)
        .attr("y", margin_elo.top - 90)
        .style("font-size", "24px")
        .style("font-weight", "bold")
        .style("font-family", "sans-serif")
        .text("Game Length Strengths");

    // set up line chart legend
    const legend_elo = svgGameLength.append("g")
        .attr("id", "legend_elo")

    legend_elo.append("text")
            .attr("class", "legend_elo-title")
            .attr("x", 490)
            .attr("y", 15)
            .style("font-weight", "bold")
            .style("font-size", "14px")
            .text("Player")
            .style("font-family", "sans-serif");

    const color_elo = d3.scaleOrdinal()
        .domain(["user", "opponent(s)"])
        .range(["#0356fc","#cc1d1d"]);

    const size = 12
    legend_elo.selectAll("mydots")
        .data(["user", "opponent(s)"])
        .enter()
        .append("rect")
        .attr("x", 490)
        .attr("y", function(d,i){ return  23 + i*(size+3)})
        .attr("width", size)
        .attr("height", size)
        .style("fill", function(d){ return color_elo(d)})

    legend_elo.selectAll("mylabels")
        .data(["user", "opponent(s)"])
        .enter()
        .append("text")
        .attr("x", 505)
        .attr("y", function(d,i){ return 23 + i*(size+4) + (size/2)})
        .attr("font-size", "14px")
        .text(function(d){ return d})
        .attr("text-anchor", "left")
        .style("alignment-baseline", "middle")

    // Dropdown change event listener-----------------------------------------------------------------------------------

    document.getElementById('elo_dropdown').addEventListener("change", function () {
        const num_opp = document.getElementById('elo_dropdown').value;

        // Update bar chart based on dropdown selection
        opp = data["opponents"];
        opp.sort((a, b) => a.rating - b.rating);
        if (num_opp === "top10") {
            opp = opp.slice(-10);
        } else if (num_opp === "bot10") {
            opp = opp.slice(0, 10);
        } else {
            opp = opp.slice(-25);
        }
        updateBarChart(opp);

        // Update line chart based on dropdown selection
        let dropdown_val = data["all_smoothed_values"]
        if(num_opp == 'top10') {
            dropdown_val = data["top10_smoothed_values"]
        } else if(num_opp == 'bot10') {
            dropdown_val = data["bot10_smoothed_values"]
        }
        updateLineChart(dropdown_val)
    });

    // line chart update------------------------------------------------------------------------------------------------

    // Function to update the chart with new data
    function updateLineChart(newData) {
        // Update scales with new data
        xScale.domain(d3.extent(newData, d => d[0]));

        // Update line path with new data
        linePath
            .datum(newData)
            .transition()
            .duration(750) // Smooth transition
            .attr("d", lineGenerator);

        // Update x-axis with new scale
        svgGameLength.select(".x-axis")
            .transition()
            .duration(750)
            .call(d3.axisBottom(xScale));
    }

    // bars mouseover handler
    var mouseover = function(d) {
        expected_val = d['opponent_smoothed_values']
        updateLineChart(expected_val)
    }

    // line graph handler on mouseout
    var mouseout = function(d) {
        const num_opp = document.getElementById('elo_dropdown').value;

        let dropdown_val = data["all_smoothed_values"]
        if(num_opp == 'top10') {
            dropdown_val = data["top10_smoothed_values"]
        } else if(num_opp == 'bot10') {
            dropdown_val = data["bot10_smoothed_values"]
        }
        updateLineChart(dropdown_val)
    }

    // bar chart update-------------------------------------------------------------------------------------------------

    function updateBarChart(opp) {
        // Update scales
        x.domain([0, d3.max(opp, d => d.rating)]);
        y.domain(opp.map(d => d.username));

        // Update axes
        svg.select(".x.axis").transition().duration(500).call(xAxis)
            .selectAll("text")
            .style("font-size", "12px");
        svg.select(".y.axis").transition().duration(500).call(yAxis)
            .selectAll("text")
            .style("font-size", "12px")
            .style("font-family", "sans-serif");

        // Bind data to bars
        const bars = svg.selectAll(".bar").data(opp);

        // Remove old bars
        bars.exit().transition().duration(500).attr("width", 0).remove();

        // Update existing bars
        bars.transition().duration(500)
            .attr("y", d => y(d.username))
            .attr("height", y.bandwidth())
            .attr("width", d => x(d.rating))
            .attr("fill", "#7d0f0f")

        // Add new bars
        bars.enter().append("rect")
            .attr("class", "bar")
            .attr("y", d => y(d.username))
            .attr("height", y.bandwidth())
            .attr("x", 0)
            .attr("width", 0)
            .attr("fill", "#7d0f0f")
            .attr("width", d => x(d.rating))
            .on("mouseover", function(d) {
                    d3.select(this).attr("fill", "#cc1d1d");
                    mouseover(d);
                    tip.show(d);
            })
            .on("mouseout", function() {
                d3.select(this).attr("fill", "#7d0f0f");
                tip.hide();
                mouseout();
            })

        // Bind data to labels
        const labels = svg.selectAll(".label").data(opp);

        // Remove old labels
        labels.exit().transition().duration(500).remove();

        // Update existing labels
        labels.transition().duration(500)
            .attr("x", d => x(d.rating) + 10)
            .attr("y", d => y(d.username) + y.bandwidth() / 2)
            .text(d => d.rating)

        // Add new labels
        labels.enter().append("text")
            .attr("class", "label")
            .attr("x", d => x(d.rating) + 10)
            .attr("y", d => y(d.username) + y.bandwidth() / 2)
            .attr("dy", ".35em")
            .style("font-family", "sans-serif")
            .style("font-size", "12px")
            // .style("font-weight", "bold")
            .style('fill', '#3c3d28')
            .text(d => d.rating);
    }
});