/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile, df_driver, costmiledriver, heatmap_values, routeefficiency_data) {
	df = new dfd.DataFrame(full_df);
	dfdriver = new dfd.DataFrame(df_driver);

	let group_df = "";
	let driver_df = "";
	if (costpermile !== "0"){
		dfcost = new dfd.DataFrame(costpermile);
		dfcostdirver = new dfd.DataFrame(costmiledriver);
		dfcost.print();
		dfcost.sortValues("CostPerMile", { inplace: true })
		group_df = dfcost.groupby(["CarrierName"]);
		driver_df = dfcostdirver.groupby(["DriverName"]);
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
	const driverspeedmpg = [];
	const driverontimempg = [];
	const driverseriesdata =[];
	const driverdata = [];
	for (let i = 0; i < dfdriver.shape[0]; i++) {
		driverseriesdata.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["MedianMPG"].values[0], dfdriver.iloc({rows: [i]})["OnTimeRate"].values[0]*100]]
		});
		if (costpermile !== "0") {
			driverspeedmpg.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["MedianMPG"].values[0], dfdriver.iloc({rows: [i]})["MedianSpeed"].values[0]]]
		});
			driverontimempg.push({
			name: dfdriver.iloc({rows: [i]})["DriverName"].values[0],
			data: [[dfdriver.iloc({rows: [i]})["OnTimeRate"].values[0]*100, dfdriver.iloc({rows: [i]})["MedianMPG"].values[0]]]
		});
			let b = driver_df.getGroup([dfdriver.iloc({rows: [i]})["DriverName"].values[0]]);
			// console.log(df.iloc({rows: [i]})["CarrierName"].values[0]);
			// console.log(a.values[1]);
			const median = d3.quantile(b["CostPerMile"].values, 0.5);
			const q1 = d3.quantile(b["CostPerMile"].values, 0.25);
			const min = d3.min(b["CostPerMile"].values);
			const max = d3.max(b["CostPerMile"].values);
			const q3 = d3.quantile(b["CostPerMile"].values, 0.75);
			driverdata.push({x: dfdriver.iloc({rows: [i]})["DriverName"].values[0], y: [min, q1, median, q3, max]})
		}
	}
	var ontimedata = dfdriver["OnTimeRate"].values;
	var mpgdata = dfdriver["MedianMPG"].values;
	var mphdata = dfdriver["MedianSpeed"].values;
	var driversname = dfdriver["DriverName"].values;
	const drivermpgmedian = dfdriver["MedianMPG"].mean();
	const driverontimemedian = dfdriver["OnTimeRate"].mean()*100;
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

// Fuel Cost per Mile Distribution by Driver
	var driverCostMileChartOptions = {
          series: [
          {
            type: 'boxPlot',
            data: driverdata
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
              upper: '#eb5849',
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

// var ScatterChartDriverSpeedMPGOptions = {
// 		series: [{
// 		name: "Median Speed (MPH)",
// 		type: 'scatter',
// 		data: driverspeedmpg,
// 		},
// 			{
// 		name: "On-Time Delivery Rate (%)",
// 		type: 'line',
//           data: driverontimempg
// 			}],
//
// 		chart: {
// 			height: 350,
// 			type: 'line',
// 			zoom: { enabled: true, type: 'xy' }
// 		},
// 		fill: {
//             opacity: 0.8
//         },
//
// 		xaxis: {
// 			tickAmount: 10,
// 			labels: {
// 				formatter: function(val) { return parseFloat(val).toFixed(1) }
// 			},
// 			title: {
// 				text: 'Median Speed (MPH)'
// 			}
// 		},
// 		yaxis: { tickAmount: 7,
// 			labels: {
// 				formatter: function(val) { return parseFloat(val).toFixed(2) }
// 			},
// 		title: {
//             text: 'Fuel Efficiency (MPG)'
//           }
// 		},
//
// 	};

var ScatterChartDriverSpeedMPGOptions = {
		series: driverspeedmpg,
		chart: {
			height: 350,
			type: 'scatter',
			zoom: { enabled: true, type: 'xy' }
		},
		fill: {
            opacity: 0.8
        },
		annotations: {
		  yaxis: [
			{
			  y: drivermedianspeed,
			  borderColor: '#00E396',
			  label: {
				borderColor: '#00E396',
				style: {
				  color: '#fff',
				  background: '#00E396'
				},
				text: 'MPH'
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

		xaxis: {
			tickAmount: 10,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(1) }
			},
			title: {
				text: 'Fuel Efficiency (MPG)'
			}
		},
		yaxis: { tickAmount: 7,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(2) }
			},
		title: {
            text: 'Median Speed (MPH)'
          }
		},

	};

var MixedDriverOnTimeMPGMPHoptions = {
          series: [{
          name: 'On-Time',
          type: 'column',
          data: ontimedata
        }, {
          name: 'MPG',
          type: 'column',
          data: mpgdata
        }, {
          name: 'MPH',
          type: 'line',
          data: mphdata
        }],
          chart: {
          height: 350,
          type: 'line',
          stacked: false
        },
        dataLabels: {
          enabled: true,
		  enabledOnSeries: [2]
        },
        stroke: {
          width: [1, 1, 4]
        },
        // title: {
        //   text: 'Driver Productivity Analysis',
        //   align: 'left',
        //   offsetX: 110
        // },
        xaxis: {
		  labels: {
            	rotate: -45
          	},
          categories: driversname,
		  tickPlacement: 'on'
        },
        yaxis: [
          {
            seriesName: 'On-Time',
            axisTicks: {
              show: true,
            },
            axisBorder: {
              show: true,
              color: '#008FFB'
            },
            labels: {
              style: {
                colors: '#008FFB',
              }
            },
            title: {
              text: "On-Time Delivery Rate (%)",
              style: {
                color: '#008FFB',
              }
            },
            tooltip: {
              enabled: true
            }
          },
          {
            seriesName: 'MPG',
            opposite: true,
            axisTicks: {
              show: true,
            },
            axisBorder: {
              show: true,
              color: '#00E396'
            },
            labels: {
              style: {
                colors: '#00E396',
              }
            },
            title: {
              text: "Fuel Efficiency (MPG)",
              style: {
                color: '#00E396',
              }
            },
          },
          {
            seriesName: 'MPH',
            opposite: true,
            axisTicks: {
              show: true,
            },
            axisBorder: {
              show: true,
              color: '#feb019'
            },
            labels: {
              style: {
                colors: '#feb019',
              },
            },
			  colors: '#feb019',
            title: {
              text: "Median Speed (MPH)",
              style: {
                color: '#feb019',
              }
            }
          },
        ],
        tooltip: {
          fixed: {
            enabled: true,
            position: 'topLeft', // topRight, topLeft, bottomRight, bottomLeft
            offsetY: 30,
            offsetX: 60
          },
        },
        legend: {
          horizontalAlign: 'left',
          offsetX: 40
        }
        };


var routesheatdmadoptions = {
          series: heatmap_values.heatmapvalues,
          chart: {
          height: 350,
          type: 'heatmap',
        },
        plotOptions: {
          heatmap: {
            // shadeIntensity: 1,
            radius: 0,
            // useFillColorAsStroke: true,
            colorScale: {
              ranges: heatmap_values.range_values
            }
          }
        },
        dataLabels: {
          enabled: false
        },
        stroke: {
          width: 1
        },

		xaxis: {
			  type: 'category',
			  categories: heatmap_values.heatmap_columns
			},
		grid: {
			  padding: {
				right: 20
			  }
			}
        };

var routesBubbleoptions = {
          series: [{
          name: 'Route Efficiency',
          data: routeefficiency_data.routeefficiency
        },

        ],
          chart: {
            height: 350,
            type: 'bubble',
        },
		theme: {
			palette: 'palette1' // Apply the first built-in palette
		},
        dataLabels: {
            enabled: false
        },
        fill: {
            opacity: 0.8
        },
        // title: {
        //     text: 'Simple Bubble Chart'
        // },
        xaxis: {
            tickAmount: routeefficiency_data.maxspeed - routeefficiency_data.minspeed - 1,
            type: 'category',
			min: routeefficiency_data.minspeed,
			max: routeefficiency_data.maxspeed,

        },
        yaxis: {
			min: routeefficiency_data.mincost,
			max: routeefficiency_data.maxcost,
			labels: {
				formatter: function(val) { return parseFloat(val).toFixed(2) }
			},
        }
        };

var routeEfficiencyBubblechart = new ApexCharts(document.querySelector("#RouteEfficiencyBubble"), routesBubbleoptions);
        routeEfficiencyBubblechart.render();

var apexHeatMapChart = new ApexCharts(document.querySelector("#RouteHeatMap"), routesheatdmadoptions);
        apexHeatMapChart.render();

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
			driverCostMileChartOptions
			);
		apexScatterDriverSpeedMPGChart.render();
	}
	// apexMixedChart
	var apexScatterDriverMpgOnTimeChart = new ApexCharts(
		document.querySelector('#DriverMpgOnTime'),
		MixedDriverOnTimeMPGMPHoptions
	);
	apexScatterDriverMpgOnTimeChart.render();


	// apexPieChart ScatterChartDriverSpeedMPGOptions ScatterChartDriverOntimeMPGOptions






};


