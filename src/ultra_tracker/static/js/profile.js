document.addEventListener('DOMContentLoaded', function() {
    var route = {
        x: distances,
        y: elevations,
        type: 'scatter',
        fill: 'tozeroy',  // Shade the area under the curve
        mode: 'lines',
        hoverinfo: 'skip',
    };

    // Create marker for the runner's position
    var runner_marker = {
        x: [runner_x],
        y: [runner_y],
        mode: 'markers',
        hoverinfo: 'x+y',
        hovertemplate: '%{x:.2f} mi, %{y:.0f} ft<extra></extra>',
        marker: {
            symbol: 'diamond-dot',
            size: 14,
            color: 'purple',
            line: {
                color: 'black',
                width: 1
            },
        },
        name: 'Runner'
    };

    var data = [route, runner_marker];

    // Create annotations for each course element
    var annotations = aid_station_annotations.map(element => ({
        x: element.x,
        y: element.y,
        xref: 'x',
        yref: 'y',
        text: element.name,
        showarrow: true,
        arrowhead: 0,
        ax: 0,
        ay: -40
    }));

    // Add the runner annotation to the array
    annotations.push({
        x: runner_x,
        y: runner_y,
        xref: 'x',
        yref: 'y',
        text: runner_name,
        showarrow: true,
        arrowhead: 0,
        ax: 0,
        ay: -40
    });


    // Define the layout with axis labels
    var layout = {
        xaxis: {
            title: 'Distance (miles)',
            range: [0, Math.max.apply(null, distances)],
            fixedrange: true,
            dtick: 5,
        },
        yaxis: {
            title: 'Elevation (feet)',
            range: [Math.min.apply(null, elevations), Math.max.apply(null, elevations)],
            autorange: false,
            fixedrange: true,
        },
        title: 'Elevation Profile',
        margin: {
            l: 50,  // left margin
            r: 50,  // right margin
            t: 50,  // top margin
            b: 50   // bottom margin
        },
        showlegend: false,
        hovermode: 'closest',
        annotations: annotations,
    };
    var config = {
      responsive: false,
      displayModeBar: false, // Hide the modebar
      scrollZoom: false, // Disable scroll to zoom
      doubleClick: false, // Disable double click interaction
      staticPlot: false // Ensure staticPlot is false to allow hover
    };
    Plotly.newPlot('profile', data, layout, config); 
});
