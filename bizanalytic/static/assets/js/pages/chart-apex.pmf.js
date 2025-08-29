/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile, df_driver) {
	df = new dfd.DataFrame(full_df);
	dfdriver = new dfd.DataFrame(df_driver);
	let group_df = "";
	if (costpermile !== "0"){
		dfcost = new dfd.DataFrame(costpermile);
		dfcost.print();
		dfcost.sortValues("CostPerMile", { inplace: true })
		group_df = dfcost.groupby(["CarrierName"]);
		console.log(group_df);
	}


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



	const seriesdata =[];
    const costdata =[];
	for (let i = 0; i < df.shape[0]; i++) {
		seriesdata.push({name: df.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgFreightCost"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});
        if (costpermile !== "0") {
			console.log(group_df);
			let a = group_df.getGroup([df.iloc({rows: [i]})["CarrierName"].values[0]]);
			// console.log(df.iloc({rows: [i]})["CarrierName"].values[0]);
			// console.log(a.values[1]);
			const median = d3.quantile(a["CostPerMile"].values, 0.5);
			const q1 = d3.quantile(a["CostPerMile"].values, 0.25);
			const min = d3.min(a["CostPerMile"].values);
			const max = d3.max(a["CostPerMile"].values);
			const q3 = d3.quantile(a["CostPerMile"].values, 0.75);
			costdata.push({x: df.iloc({rows: [i]})["CarrierName"].values[0], y: [min, q1, median, q3, max]})
		}
		// console.log(costdata);
	}
	console.log("seriesdata", seriesdata);
	const driverspeedmpg = []
	const driverseriesdata =[];
	for (let i = 0; i < dfdriver.shape[0]; i++) {
		driverseriesdata.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["MedianMPG"].values[0], dfdriver.iloc({rows: [i]})["OnTimeRate"].values[0]*100]]
		});
		if (costpermile !== "0") {
			driverspeedmpg.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["MedianSpeed"].values[0], dfdriver.iloc({rows: [i]})["MedianMPG"].values[0], dfdriver.iloc({rows: [i]})["OnTimeRate"].values[0]*100]]
		});
		}
	}
	const drivermpgmedian = dfdriver["MedianMPG"].mean();
	const driverontimemedian = dfdriver["OnTimeRate"].median()*100;
	const drivermedianspeed = dfdriver["MedianSpeed"].mean();
	const carrierfreightcostmedian = d3.quantile(df["AvgFreightCost"].values, 0.75);
	const carrierontimemedian = d3.quantile(df["OnTimeRate"].values, 0.75);

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
		annotations: {
		  yaxis: [
			{
			  y: carrierontimemedian,
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
				  x: carrierfreightcostmedian,
				  borderColor: '#086bda',
				  label: {
					borderColor: '#086bda',
					style: {
					  color: '#fff',
					  background: '#086bda'
					},
					text: 'Cost/Mile'
				  }
				}
			  ],
		},
		// colors: [app.color.theme, app.color.warning, 'rgba('+ app.color.bodyColorRgb + ', .5)'],
		series: seriesdata,
		xaxis: {
			tickAmount: 10,
			labels: {
				// formatter: function(val) { return parseFloat(val).toFixed(2) }
			},
			title: {
					text: 'Average Freight Cost ($)'
			}
		},
		yaxis: { tickAmount: 7,
		title: {
            text: 'On-Time Delivery Rate (%)'
          }
		}
	};

var ScatterChartDriverOntimeMPGOptions = {
		chart: {
			height: 350,
			type: 'scatter',
			zoom: { enabled: true, type: 'xy' }
		},
		annotations: {
		  yaxis: [
			{
			  y: driverontimemedian,
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
				  x: drivermpgmedian,
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
				formatter: function(val) { return parseFloat(val).toFixed(2) }
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

	};

var ScatterChartDriverSpeedMPGOptions = {
		series: driverspeedmpg,
		chart: {
			height: 350,
			type: 'bubble',
			zoom: { enabled: true, type: 'xy' }
		},
		fill: {
            opacity: 0.8
        },
		annotations: {
		  yaxis: [
			{
			  y: drivermpgmedian,
			  borderColor: '#00E396',
			  label: {
				borderColor: '#00E396',
				style: {
				  color: '#fff',
				  background: '#00E396'
				},
				text: 'MPG'
			  }
			}
		  ],
			xaxis: [
				{
				  x: drivermedianspeed,
				  borderColor: '#086bda',
				  label: {
					borderColor: '#086bda',
					style: {
					  color: '#fff',
					  background: '#086bda'
					},
					text: 'MPH'
				  }
				}
			  ],
		},
		// colors: [app.color.theme, app.color.warning, 'rgba('+ app.color.bodyColorRgb + ', .5)'],

		xaxis: {
			tickAmount: 10,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(1) }
			},
			title: {
				text: 'Median Speed (MPH)'
			}
		},
		yaxis: { tickAmount: 7,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(2) }
			},
		title: {
            text: 'Fuel Efficiency (MPG)'
          }
		},

	};


var apexScatterCarrierCostChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterCarrierCostChart.render();
	if (costpermile !== "0") {
		var apexCostMilechart = new ApexCharts(document.querySelector("#CarrierCostPerMile"),
			apexCostMileChartOptions);
		apexCostMilechart.render();

		var apexScatterDriverSpeedMPGChart = new ApexCharts(
		document.querySelector('#DriverSpeedMPG'),
			ScatterChartDriverSpeedMPGOptions);
		apexScatterDriverSpeedMPGChart.render();
	}
	// apexMixedChart
	var apexScatterDriverMpgOnTimeChart = new ApexCharts(
		document.querySelector('#DriverMpgOnTime'),
		ScatterChartDriverOntimeMPGOptions
	);
	apexScatterDriverMpgOnTimeChart.render();


	// apexPieChart






};


