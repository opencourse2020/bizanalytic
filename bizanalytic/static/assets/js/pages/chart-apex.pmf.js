/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile) {
	df = new dfd.DataFrame(full_df);

	dfcost = new dfd.DataFrame(costpermile);
	// let carrierdata = df[['CarrierName', 'AvgFreightCost', 'OnTimeRate']];
	// console.log(carrierdata);
	let numcarrieres = df['CarrierName'].count()
	console.log(numcarrieres);
	let carrierscatterdata = [];
	// for (const row of df.itertuples()){
	// 	carrierscatterdata.push("{ name: '" + row.CarrierName +"', data: "  [[row.AvgFreightCost, row.OnTimeRate]] + " },");
	// 	}
    // console.log(`Index: ${row._index}, Col1: ${row.col1}, Col2: ${row.col2}, Col3: ${row.col3}`);
  	console.log(carrierscatterdata);


	const seriesdata =[];

	for (let i = 0; i < df.shape[0]; i++) {
		seriesdata.push({name: df.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgCostPerMile"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});
	}

	const costdata =[];
	let group_df = df.groupby(["CarrierName"]);
	console.log(group_df);
	// for (let i = 0; i < dfcost.shape[0]; i++) {
	// 	console.log(df.iloc({rows: [i]})["CarrierName"].values[0]);
	// 	console.log(df.iloc({rows: [i]})["AvgCostPerMile"].values[0]);
	// 	console.log(df.iloc({rows: [i]})["OnTimeRate"].values[0]);
	// 	costdata.push({x: dfcost.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgCostPerMile"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});
	// }


	var options = {
          series: [
          {
            type: 'boxPlot',
            data: [
              {
                x: 'Jan 2015',
                y: [54, 66, 69, 75, 88]
              },
              {
                x: 'Jan 2016',
                y: [43, 65, 69, 76, 81]
              },
              {
                x: 'Jan 2017',
                y: [31, 39, 45, 51, 59]
              },
              {
                x: 'Jan 2018',
                y: [39, 46, 55, 65, 71]
              },
              {
                x: 'Jan 2019',
                y: [29, 31, 35, 39, 44]
              },
              {
                x: 'Jan 2020',
                y: [41, 49, 58, 61, 67]
              },
              {
                x: 'Jan 2021',
                y: [54, 59, 66, 71, 88]
              }
            ]
          }
        ],
          chart: {
          type: 'boxPlot',
          height: 350
        },
        title: {
          text: 'Basic BoxPlot Chart',
          align: 'left'
        },
        plotOptions: {
          boxPlot: {
            colors: {
              upper: '#5C4742',
              lower: '#A5978B'
            }
          }
        }
        };

	// Apex = {
	// 	title: {
	// 		style: {
	// 			fontSize: '14px',
	// 			fontWeight: '600',
	// 			fontFamily: app.font.bodyFontFamily,
	// 			color: app.color.bodyColor
	// 		}
	// 	},
	// 	legend: {
	// 		show:true,
	// 		fontFamily: app.font.bodyFontFamily,
	// 		labels: { colors: app.color.bodyColor }
	// 	},
	// 	tooltip: {
	// 		style: {
    //     fontSize: '12px',
    //     fontFamily: app.font.bodyFontFamily
    //   }
	// 	},
	// 	grid: { borderColor: app.color.borderColor },
	// 	dataLabels: {
	// 		style: {
	// 			fontSize: '12px',
	// 			fontFamily: app.font.bodyFontFamily,
	// 			fontWeight: '600',
	// 			colors: undefined
  	// 	}
	// 	},
	// 	xaxis: {
	// 		axisBorder: {
	// 			show: true,
	// 			color: app.color.borderColor,
	// 			height: 1,
	// 			width: '100%',
	// 			offsetX: 0,
	// 			offsetY: -1
	// 		},
	// 		axisTicks: {
	// 			show: true,
	// 			borderType: 'solid',
	// 			color: app.color.borderColor,
	// 			height: 6,
	// 			offsetX: 0,
	// 			offsetY: 0
	// 		},
    //   labels: {
	// 			style: {
	// 				colors: app.color.bodyColor,
	// 				fontSize: '12px',
	// 				fontFamily: app.font.bodyFontFamily,
	// 				fontWeight: app.font.bodyFontWeight,
	// 				cssClass: 'apexcharts-xaxis-label',
	// 			}
	// 		}
	// 	},
	// 	yaxis: {
	// 		labels: {
	// 			formatter: function (val) {
	// 				return val.toFixed(0);
	// 			},
	// 			style: {
	// 				colors: app.color.bodyColor,
	// 				fontSize: '12px',
	// 				fontFamily: app.font.bodyFontFamily,
	// 				fontWeight: app.font.bodyFontWeight,
	// 				cssClass: 'apexcharts-yaxis-label',
	// 			},
	//
	// 		}
	// 	}
	// };

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
				formatter: function(val) { return parseFloat(val).toFixed(3) }
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

// Fuel Cost per Mile Distribution by Carrier
	var apexCostMileChartOptions = {
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
				formatter: function(val) { return parseFloat(val).toFixed(3) }
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

	var apexScatterChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterChart.render();

	// apexMixedChart


	// apexPieChart






};


