/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df) {
	df = new dfd.DataFrame(full_df);
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
		cdata = {name: df.iloc({rows: [i]})["CarrierName"].values[0], data: [[df.iloc({rows: [i]})["AvgFreightCost"].values[0], df.iloc({rows: [i]})["OnTimeRate"].values[0]]]};
		seriesdata.push({cdata})
	}
	// var options = {series: seriesdata};
	console.log(seriesdata);

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

// apexScatterChart
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
				formatter: function(val) { return parseFloat(val).toFixed(1) }
			}
		},
		yaxis: { tickAmount: 7 }
	}
	var apexScatterChart = new ApexCharts(
		document.querySelector('#CarrierCostReliabilityChart'),
		apexScatterChartOptions
	);
	apexScatterChart.render();

	// apexMixedChart


	// apexPieChart






};


