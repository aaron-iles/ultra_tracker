$(document).ready(function(){
    $(".tab-link").on("click", function(){
        var tabId = $(this).attr("href");
        $(".tab-content").removeClass("active");
        $(".tab-link").removeClass("active"); // Remove active class from all tabs
        $(this).addClass("active"); // Add active class to the clicked tab
        $(tabId).addClass("active");
        // Store selected tab in local storage
        localStorage.setItem('selectedTab', tabId);
    });
    // Check if there's a selected tab in local storage and activate it
    var selectedTab = localStorage.getItem('selectedTab');
    if (selectedTab) {
        $(selectedTab).addClass('active');
        $('a[href="' + selectedTab + '"]').addClass('active');
    }
});


document.addEventListener('DOMContentLoaded', function() {
  Prism.highlightAll();
});


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
        annotations: [
            {
                x: runner_x,
                y: runner_y,
                xref: 'x',
                yref: 'y',
                text: 'Aaron',
                showarrow: true,
                arrowhead: 0,
                ax: 0,
                ay: -40
            }
        ]
    };
    var config = {
      responsive: false,
      displayModeBar: false, // Hide the modebar
      scrollZoom: false, // Disable scroll to zoom
      doubleClick: false, // Disable double click interaction
      staticPlot: false // Ensure staticPlot is false to allow hover
    };
    Plotly.newPlot('profile', data, layout, config); 
    setInterval(fetchDataAndUpdatePlot, 10000);
});
