/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df, costpermile) {
	df = new dfd.DataFrame(full_df);

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


	// console.log(group_df);
	// for (let i = 0; i < dfcost.shape[0]; i++) {
	// 	console.log(df.iloc({rows: [i]})["CarrierName"].values[0]);
	// 	console.log(df.iloc({rows: [i]})["AvgCostPerMile"].values[0]);
	// 	console.log(df.iloc({rows: [i]})["OnTimeRate"].values[0]);
	// 	costdata.push({x: dfcost.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgCostPerMile"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]});
	// }

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
        plotOptions: {
          boxPlot: {
            colors: {
              upper: '#08e791',
              lower: '#4a89dc'
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




	var apexScatterChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterChart.render();

    var apexCostMilechart = new ApexCharts(document.querySelector("#CarrierCostPerMile"),
        apexCostMileChartOptions);
    apexCostMilechart.render();
	// apexMixedChart


	// apexPieChart






};


