/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile, df_driver, costmiledriver, heatmap_values, fleetscore) {
	df = new dfd.DataFrame(full_df);
	dfdriver = new dfd.DataFrame(df_driver);

	if (costpermile !== "0"){
		dfcost = new dfd.DataFrame(costpermile);
		dfcostdirver = new dfd.DataFrame(costmiledriver);
		dfcost.print();
		dfcost.sortValues("CostPerMile", { inplace: true })
	}


	const seriesdata =[];
	for (let i = 0; i < df.shape[0]; i++) {
		seriesdata.push({name: df.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgFreightCost"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});

	}

	var ontimedata = dfdriver["OnTimeRate"].values;
	var mpgdata = dfdriver["MedianMPG"].values;
	var mphdata = dfdriver["MedianSpeed"].values;
	var driversname = dfdriver["DriverName"].values;

	const carrierfreightcostmedian = d3.quantile(df["AvgFreightCost"].values, 0.75);
	const carrierontimemedian = d3.quantile(df["OnTimeRate"].values, 0.75);



// Carrier Cost vs. Reliability Analysis
	var apexScatterChartOptions = {
		chart: {
			height: 350,
			type: 'scatter',
			zoom: { enabled: true, type: 'xy' },
            redrawOnParentResize: true

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
          stacked: false,
          redrawOnParentResize: true

        },
        dataLabels: {
          enabled: true,
		  enabledOnSeries: [2]
        },
        stroke: {
          width: [1, 1, 4]
        },

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
          redrawOnParentResize: true

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


var fleetscorechartoptions = {
          series: [fleetscore],
          chart: {
          height: 350,
          type: 'radialBar',
        },
        plotOptions: {
          radialBar: {
            hollow: {
              size: 'OF 100',
            }
          },
        },
        labels: [fleetscore],
        };

var fleetscorechart = new ApexCharts(document.querySelector("#fleetscorechart"), fleetscorechartoptions);
        fleetscorechart.render();


var apexHeatMapChart = new ApexCharts(document.querySelector("#RouteHeatMap"), routesheatdmadoptions);
        apexHeatMapChart.render();

var apexScatterCarrierCostChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterCarrierCostChart.render();

	// apexMixedChart
var apexScatterDriverMpgOnTimeChart = new ApexCharts(
		document.querySelector('#DriverMpgOnTime'),
		MixedDriverOnTimeMPGMPHoptions
	);
	apexScatterDriverMpgOnTimeChart.render();


	// apexPieChart ScatterChartDriverSpeedMPGOptions ScatterChartDriverOntimeMPGOptions






};


