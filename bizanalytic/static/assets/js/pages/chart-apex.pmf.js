/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile, df_driver) {
	df = new dfd.DataFrame(full_df);
	dfdriver = new dfd.DataFrame(df_driver);
	dfcost = new dfd.DataFrame(costpermile);
	dfcost.sortValues("CostPerMile", { inplace: true })
	// let carrierdata = df[['CarrierName', 'AvgFreightCost', 'OnTimeRate']];
	// console.log(carrierdata);
	let numcarrieres = df['CarrierName'].count()
	// console.log(numcarrieres);
	let carrierscatterdata = [];
	// for (const row of df.itertuples()){
	// 	carrierscatterdata.push("{ name: '" + row.CarrierName +"', data: "  [[row.AvgFreightCost, row.OnTimeRate]] + " },");
	// 	}
    // console.log(`Index: ${row._index}, Col1: ${row.col1}, Col2: ${row.col2}, Col3: ${row.col3}`);
  	// console.log(carrierscatterdata);

    let group_df = dfcost.groupby(["CarrierName"]);

	const seriesdata =[];
    const costdata =[];
	for (let i = 0; i < df.shape[0]; i++) {
		seriesdata.push({name: df.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgCostPerMile"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});
        let a = group_df.getGroup([df.iloc({rows: [i]})["CarrierName"].values[0]]);
		// console.log(df.iloc({rows: [i]})["CarrierName"].values[0]);
		// console.log(a.values[1]);
		const median = d3.quantile(a["CostPerMile"].values, 0.5);
		const q1 = d3.quantile(a["CostPerMile"].values, 0.25);
		const min = d3.min(a["CostPerMile"].values);
		const max = d3.max(a["CostPerMile"].values);
		const q3 = d3.quantile(a["CostPerMile"].values, 0.75);
        costdata.push({x: df.iloc({rows: [i]})["CarrierName"].values[0], y: [min, q1, median, q3, max]})
		// console.log(costdata);
	}

	const driverseriesdata =[];
	for (let i = 0; i < dfdriver.shape[0]; i++) {
		driverseriesdata.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["MedianMPG"].values[0], dfdriver.iloc({rows: [i]})["OnTimeRate"].values[0]]]
		});
	}
	const mpgmedian = dfdriver["MedianMPG"].median();
	const ontimemedian = dfdriver["OnTimeRate"].median();

// Fuel Cost per Mile Distribution by Carrier
	var apexCostMileChartOptions = {
          series: [
          {
            type: 'boxPlot',
            data: costdata
          }
        ],
          chart: {
          type: 'boxPlot',
          height: 350
        },
        title: {
          // text: 'Basic BoxPlot Chart',
          align: 'left'
        },
		yaxis: {
			  labels: {
				formatter: function(val) { return parseFloat(val).toFixed(4) }
			},
		},
        plotOptions: {
          boxPlot: {
            colors: {
              upper: '#08e791',
              lower: '#4a89dc'
            }
          }
        }
        };


// Carrier Cost vs. Reliability Analysis
	var apexScatterChartOptions = {
		chart: {
			height: 350,
			type: 'scatter',
			zoom: { enabled: true, type: 'xy' }
		},
		// colors: [app.color.theme, app.color.warning, 'rgba('+ app.color.bodyColorRgb + ', .5)'],
		series: seriesdata,
		xaxis: {
			tickAmount: 10,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(4) }
			},
			title: {
				text: 'Average Cost/Mile ($)'
			}
		},
		yaxis: { tickAmount: 7,
		title: {
            text: 'On-Time Delivery Rate (%)'
          }
		}
	}

var apexScatterDriverChartOptions = {
		chart: {
			height: 350,
			type: 'scatter',
			zoom: { enabled: true, type: 'xy' }
		},
		annotations: {
		  yaxis: [
			{
			  y: ontimemedian,
			  borderColor: '#00E396',
			  label: {
				borderColor: '#00E396',
				style: {
				  color: '#fff',
				  background: '#00E396'
				},
				text: 'On-Time'
			  }
			}
		  ],
			xaxis: [
				{
				  x: mpgmedian,
				  borderColor: '#086bda',
				  label: {
					borderColor: '#086bda',
					style: {
					  color: '#fff',
					  background: '#086bda'
					},
					text: 'MPG'
				  }
				}
			  ],
		},
		// colors: [app.color.theme, app.color.warning, 'rgba('+ app.color.bodyColorRgb + ', .5)'],
		series: driverseriesdata,
		xaxis: {
			tickAmount: 10,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(3) }
			},
			title: {
				text: 'Fuel Efficiency (MPG)'
			}
		},
		yaxis: { tickAmount: 7,
		title: {
            text: 'On-Time Delivery Rate (%)'
          }
		},

	}


	var apexScatterChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterChart.render();

    var apexCostMilechart = new ApexCharts(document.querySelector("#CarrierCostPerMile"),
        apexCostMileChartOptions);
    apexCostMilechart.render();

	// apexMixedChart
	var apexScatterChart = new ApexCharts(
		document.querySelector('#DriverMpgOnTime'),
		apexScatterDriverChartOptions
	);
	apexScatterChart.render();


	// apexPieChart






};


