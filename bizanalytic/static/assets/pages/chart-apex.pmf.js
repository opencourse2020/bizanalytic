/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 2.4.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

var handleRenderApexChart = function(full_df) {
	df = new dfd.DataFrame(full_df);
	var cat = df['cohort_rep'].values;
	var data1 = df['new'].values;
	var data2 = df['churned'].abs().values;
	var data3 = df['contraction'].abs().values;


	total_new = df['new'].sum();
	total_resurrected = df['resurrected'].sum();
	total_expansion = df['expansion'].sum();
	total_retained = df['retained'].sum();
	total_growth = total_new + total_resurrected + total_expansion + total_retained;
	perc_new = (total_new/total_growth)*100;
	perc_resurrected = (total_resurrected/total_growth)*100;
	perc_expansion = (total_expansion/total_growth)*100;
	perc_retained = (total_retained/total_growth)*100;
	existing = df['resurrected'].add(df['expansion']).values;
	existing_df = df['resurrected'].add(df['expansion']);
	total_existing = total_resurrected + total_expansion;
	total_gain = total_existing + total_new;
	perc_news = ((total_new/total_gain)*100).toFixed(2);
	perc_existing = ((total_existing/total_gain)*100).toFixed(2);
	max_new = df['new'].max();
	min_new = df['new'].min();
	mean_new = df['new'].mean();
	std_new = df['new'].std();
	max_existing = existing_df.max();
	min_existing = existing_df.min();
	mean_existing = existing_df.mean();
	std_existing = existing_df.std();



	total_churn = Math.abs(df['churned'].sum());
	total_contraction = Math.abs(df['contraction'].sum());
	total_losses = total_contraction + total_churn;
	perc_contractions = ((total_contraction/total_losses)*100).toFixed(2);
	perc_churn = ((total_churn/total_losses)*100).toFixed(2);
	max_contractions = df['contraction'].abs().max();
	min_contractions = df['contraction'].abs().min();
	mean_contractions = df['contraction'].abs().mean();
	std_contractions = df['contraction'].abs().std();
	max_churn = df['churned'].abs().max();
	min_churn = df['churned'].abs().min();
	mean_churn = df['churned'].abs().mean();
	std_churn = df['churned'].abs().std();


	new_rate = df['new_rate'].values;
	resurrected_rate = df['resurrected_rate'].values;
	expansion_rate = df['expansion_rate'].values;
	retained_rate = df['retained_rate'].values;
	churned_rate = df['churned_rate'].values;
	growth_rate = df['growth_rate'].values;
	quick_ratio = df['quick_ratio'].values;
	gross_retention = df['gross_retention'].values;
	net_churn = df['net_churn'].values;
	max_rate = df['new_rate'].max();


	document.getElementById("total_losses").innerHTML = total_losses + ' Losses';
	// document.getElementById("total_contractions").innerHTML = total_contraction;
	// document.getElementById("total_churn").innerHTML = total_churn;
	document.getElementById("perc_contractions").innerHTML = perc_contractions + '%';
	document.getElementById("perc_churn").innerHTML = perc_churn + '%';
	document.getElementById("max_contractions").innerHTML = max_contractions;
	document.getElementById("min_contractions").innerHTML = min_contractions;
	document.getElementById("mean_contractions").innerHTML = mean_contractions.toFixed(2);
	document.getElementById("std_contractions").innerHTML = std_contractions.toFixed(2);
	document.getElementById("max_churn").innerHTML = max_churn;
	document.getElementById("min_churn").innerHTML = min_churn;
	document.getElementById("mean_churn").innerHTML = mean_churn.toFixed(2);
	document.getElementById("std_churn").innerHTML = std_churn.toFixed(2);

	document.getElementById("total_gain").innerHTML = total_gain + ' Extra';
	document.getElementById("perc_new").innerHTML = perc_news + '%';
	document.getElementById("perc_existing").innerHTML = perc_existing + '%';
	document.getElementById("max_new").innerHTML = max_new;
	document.getElementById("min_new").innerHTML = min_new;
	document.getElementById("mean_new").innerHTML = mean_new.toFixed(2);
	document.getElementById("std_new").innerHTML = std_new.toFixed(2);
	document.getElementById("max_existing").innerHTML = max_existing;
	document.getElementById("min_existing").innerHTML = min_existing;
	document.getElementById("mean_existing").innerHTML = mean_existing.toFixed(2);
	document.getElementById("std_existing").innerHTML = std_existing.toFixed(2);

	// if (df['resurrected_rate'] > max_rate)
	// {
	// 	max_rate = df['resurrected_rate'].max();
	// }
	if (df['expansion_rate'].max() > max_rate){
		max_rate = df['expansion_rate'].max();
	}
	// if(df['retained_rate'].max() > max_rate){
	// 	max_rate = df['retained_rate'].max();
	// }

	min_rate = df['new_rate'].min();
	// if (df['resurrected_rate'] < min_rate)
	// {
	// 	min_rate = df['resurrected_rate'].min();
	// }
	if (df['expansion_rate'].min() < min_rate){
		min_rate = df['expansion_rate'].min();
	}
	// if(df['retained_rate'].min() < min_rate){
	// 	min_rate = df['retained_rate'].min();
	// }

	min_churn_rate = df['churned_rate'].min();
	if (df['growth_rate'].min() < min_churn_rate){
		min_churn_rate = df['growth_rate'].min();
	}
	min_churn_rate = Math.round(min_churn_rate);

	max_rate =max_rate + 1;
	min_rate =min_rate - 1;
	// console.log(total_churn);
	// console.log(total_contraction);
	// console.log(total_expansion);
	// console.log(total_retained);

	// cat, data1,data2,data3,data1_name,data2_name,data3_name,data1_title,data2_title,data3_title
	Apex = {
		title: {
			style: {
				fontSize: '14px',
				fontWeight: '600',
				fontFamily: app.font.bodyFontFamily,
				color: app.color.bodyColor
			}
		},
		legend: {
			show:true,
			fontFamily: app.font.bodyFontFamily,
			labels: { colors: app.color.bodyColor }
		},
		tooltip: {
			style: {
        fontSize: '12px',
        fontFamily: app.font.bodyFontFamily
      }
		},
		grid: { borderColor: app.color.borderColor },
		dataLabels: {
			style: {
				fontSize: '12px',
				fontFamily: app.font.bodyFontFamily,
				fontWeight: '600',
				colors: undefined
  		}
		},
		xaxis: {
			axisBorder: {
				show: true,
				color: app.color.borderColor,
				height: 1,
				width: '100%',
				offsetX: 0,
				offsetY: -1
			},
			axisTicks: {
				show: true,
				borderType: 'solid',
				color: app.color.borderColor,
				height: 6,
				offsetX: 0,
				offsetY: 0
			},
      labels: {
				style: {
					colors: app.color.bodyColor,
					fontSize: '12px',
					fontFamily: app.font.bodyFontFamily,
					fontWeight: app.font.bodyFontWeight,
					cssClass: 'apexcharts-xaxis-label',
				}
			}
		},
		yaxis: {
			labels: {
				formatter: function (val) {
					return val.toFixed(0);
				},
				style: {
					colors: app.color.bodyColor,
					fontSize: '12px',
					fontFamily: app.font.bodyFontFamily,
					fontWeight: app.font.bodyFontWeight,
					cssClass: 'apexcharts-yaxis-label',
				},

			}
		}
	};


	// apexMixedChart
	var apexMixedChartOptions = {
		chart: {
			height: '100%',
			type: 'line',
			stacked: false,
			zoom: {
            enabled: false
          },
          toolbar: {
            show: false
          }
		},
		dataLabels: { enabled: false },
		series: [
			{ name: 'Churned', type: 'column', data: data2 },
			{ name: 'Contraction', type: 'column', data: data3 },
			// { name: 'Contraction', type: 'line', data: data3 }
		],
		stroke: { width: [0, 3] },
		colors: [app.color.theme, app.color.warning],
		title: {
			// text: 'Churn Analysis',
			align: 'left',
			offsetX: 110
		},
		xaxis: {
			categories: cat,
			axisBorder: {
				show: true,
				color: app.color.borderColor,
				height: 1,
				width: '100%',
				offsetX: 0,
				offsetY: -1
			},
			axisTicks: {
				show: true,
				borderType: 'solid',
				color: app.color.borderColor,
				height: 6,
				offsetX: 0,
				offsetY: 0
			}
		},
		yaxis: [
			{
			axisTicks: {show: true, color: app.color.borderColor},
			axisBorder: {show: true, color: app.color.theme},
			labels: {
				formatter: function (val) {
					return val.toFixed(0);
				},
				style: {colors: [app.color.bodyColor]}
			},
			title: {
				text: 'Churned',
				style: {color: app.color.theme}
			},
			tooltip: {enabled: true}
		},
		{
			seriesName: 'Contraction',
			opposite: true,
			axisTicks: { show: true, color: app.color.borderColor },
			axisBorder: { show: true, color: app.color.warning },
			labels: {
				formatter: function (val) {
					return val.toFixed(0);
				},
				style: { colors: [app.color.bodyColor] } },
			title: {
				text: 'Contraction',
				style: { color: app.color.warning }
			},
		},
		// 	{
		// 	seriesName: 'Contraction',
		// 	opposite: true,
		// 	axisTicks: { show: true, color: app.color.borderColor },
		// 	axisBorder: { show: true, color: app.color.warning },
		// 	labels: { style: { colors: [app.color.bodyColor] } },
		// 	title: {
		// 		text: 'Contraction',
		// 		style: { color: app.color.warning }
		// 	}
		// }
		],
		tooltip: {
			fixed: {
				enabled: true,
				position: 'topLeft',
				offsetY: 30,
				offsetX: 60
			},
		},
		// legend: {
		// 	show: false
		//   }
		legend: { position: 'top', horizontalAlign: 'center' }
	};
	var apexMixedChart = new ApexCharts(
		document.querySelector('#apexMixedChart'),
		apexMixedChartOptions
	);
	apexMixedChart.render();

	// apexPieChart
	var positiveinteractionsPieChartOptions = {
		chart: {
			height: 365,
			type: 'donut',
		},
		dataLabels: {
			dropShadow: {
				enabled: false,
				top: 1,
				left: 1,
				blur: 1,
				opacity: 1
			},
			style: {
				colors: ['#000']
			},
			// formatter(val, opts) {
          //   const name = opts.w.globals.labels[opts.seriesIndex]
          //   return [name, val.toFixed(1) + '%']
          // }


		},
		stroke: {
          show: false
        },
		// colors: [ 'rgba('+ app.color.pinkRgb +', .75)',  'rgba('+ app.color.warningRgb +', .75)',  'rgba('+app.color.theme +', .75)'],
		labels: ['New', 'Resurected', 'Expansion'],
		series: [total_new, total_resurrected, total_expansion],
		// legend: {
        //   show: false
        // }
		// responsive: [{
        //   breakpoint: 480,
        //   options: {
        //     chart: {
        //       width: 200
        //     },
        //     legend: {
        //       position: 'bottom'
        //     }
        //   }
        // }]
		// title: { text: 'Positive User interactions' }
	};
	var positivePieChart = new ApexCharts(
		document.querySelector('#positiveChartPie'),
		positiveinteractionsPieChartOptions
	);
	positivePieChart.render();

	var negativeinteractionsPieChartOptions = {
		chart: {
			height: 365,
			type: 'pie',
		},
		dataLabels: {
			dropShadow: {
				enabled: false,
				top: 1,
				left: 1,
				blur: 1,
				opacity: 1
			},
			style: {
				colors: ['#333']
			},
		},
		stroke: { show: false },
		colors: [ 'rgba('+app.color.themeRgb +', .75)',  'rgba(255,255,255, .75)'],
		labels: ['Churn', 'Contractions'],
		series: [total_churn, total_contraction],
		// title: { text: 'Negative User interactions' }
	};
	var negativePieChart = new ApexCharts(
		document.querySelector('#negativeChartPie'),
		negativeinteractionsPieChartOptions
	);
	negativePieChart.render();

	// apexLineChart
	var positivegrowthColumnChartOptions = {
		 		chart: {
			height: '100%',
			type: 'line',
			stacked: false,
			zoom: {
            enabled: false
          },
          toolbar: {
            show: false
          }
		},
		dataLabels: { enabled: false },
		series: [
			{ name: 'New', type: 'column', data: data1 },
			{ name: 'Existing', type: 'column', data: existing },
			// { name: 'Contraction', type: 'line', data: data3 }
		],
		stroke: { width: [0, 3] },
		colors: [app.color.theme, app.color.warning],
		title: {
			// text: 'Churn Analysis',
			align: 'left',
			offsetX: 110
		},
		xaxis: {
			categories: cat,
			axisBorder: {
				show: true,
				color: app.color.borderColor,
				height: 1,
				width: '100%',
				offsetX: 0,
				offsetY: -1
			},
			axisTicks: {
				show: true,
				borderType: 'solid',
				color: app.color.borderColor,
				height: 6,
				offsetX: 0,
				offsetY: 0
			}
		},
		yaxis: [
			{
			axisTicks: {show: true, color: app.color.borderColor},
			axisBorder: {show: true, color: app.color.theme},
			labels: {
				formatter: function (val) {
					return val.toFixed(0);
				},
				style: {colors: [app.color.bodyColor]}
			},
			title: {
				text: 'New',
				style: {color: app.color.theme}
			},
			tooltip: {enabled: true}
		},
		{
			seriesName: 'Existing',
			opposite: true,
			axisTicks: { show: true, color: app.color.borderColor },
			axisBorder: { show: true, color: app.color.warning },
			labels: {
				formatter: function (val) {
					return val.toFixed(0);
				},
				style: { colors: [app.color.bodyColor] } },
			title: {
				text: 'Existing',
				style: { color: app.color.warning }
			},
		},

		],
		tooltip: {
			fixed: {
				enabled: true,
				position: 'topLeft',
				offsetY: 30,
				offsetX: 60
			},
		},
		// legend: {
		// 	show: false
		//   }
		legend: { position: 'top', horizontalAlign: 'center' }
	};
	var apexLineChart = new ApexCharts(
		document.querySelector('#positiveColumnChart'),
		positivegrowthColumnChartOptions
	);
	apexLineChart.render();


	// apexAreaChart
	var resurectedretainedChartOptions = {
		chart: {
			height: 350,
			type: 'area',
			zoom: {
            enabled: false
          },
          toolbar: {
            show: false
          }
		},
		dataLabels: { enabled: false },
		stroke: { curve: 'smooth', width: 3 },
		colors: [app.color.teal, app.color.warning],
		series: [
			{ name: 'Resurrected Rate', data: resurrected_rate },
			{ name: 'Retained Rate', data: retained_rate }
		],
		xaxis: {

			categories: cat,
			axisBorder: {
				show: true,
				color: app.color.borderColor,
				height: 1,
				width: '100%',
				offsetX: 0,
				offsetY: -1
			},
			axisTicks: {
				show: true,
				borderType: 'solid',
				color: app.color.borderColor,
				height: 6,
				offsetX: 0,
				offsetY: 0
			}
		},
		yaxis: [{
			 axisTicks: {show: true, color: app.color.borderColor},
			axisBorder: {show: true, color: app.color.theme},
			labels: {

				style: {colors: [app.color.bodyColor]}
			},
          title: {
            // text: 'New Rates',
			style: {color: app.color.theme}
          },
          // min: 0,
          // max: 4
        },
		{
			axisTicks: {show: true, color: app.color.borderColor},
			axisBorder: {show: true, color: app.color.warning},
			labels: {

				style: {colors: [app.color.bodyColor]}
			},
		  opposite: true,
          title: {
            // text: 'Expansion Rates',
			style: {color: app.color.warning}
          },
          // min: 0,
          // max: 4
        }
		],
		tooltip: {
			// fixed: {
			// 	enabled: true,
			// 	position: 'topLeft',
			// 	offsetY: 30,
			// 	offsetX: 60
			// },
		},
		// title: { text: 'Resurrected Vs. Retained Rates' }
	};
	var resurectedretainedAreaChart = new ApexCharts(
		document.querySelector('#resurectedretainedChart'),
		resurectedretainedChartOptions
	);
	resurectedretainedAreaChart.render();

	var churnedgrowthChartOptions = {
		chart: {
			height: 350,
			type: 'area',
			zoom: {
            enabled: false
          },
          toolbar: {
            show: false
          }
		},
		dataLabels: { enabled: false },
		stroke: { curve: 'smooth', width: 3 },
		colors: [app.color.inverse, 'rgba('+ app.color.pinkRgb +', .75)'],
		series: [
			{ name: 'Quick Ratio', data: quick_ratio },
			{ name: 'Growth Rate', data: growth_rate }
		],
		xaxis: {

			categories: cat,
			axisBorder: {
				show: true,
				color: app.color.borderColor,
				height: 1,
				width: '100%',
				offsetX: 0,
				offsetY: -1
			},
			axisTicks: {
				show: true,
				borderType: 'solid',
				color: app.color.borderColor,
				height: 6,
				offsetX: 0,
				offsetY: 0
			}
		},
		// yaxis: [{
		// 	 axisTicks: {show: true, color: app.color.borderColor},
		// 	axisBorder: {show: true, color: app.color.inverse},
		// 	labels: {
		//
		// 		style: {colors: [app.color.bodyColor]}
		// 	},
        //   title: {
        //     // text: 'New Rates',
		// 	style: {color: app.color.theme}
        //   },
        //   min: min_churn_rate,
        //   // max: 4
        // },
		// {
		// 	axisTicks: {show: true, color: app.color.borderColor},
		// 	axisBorder: {show: true, color: app.color.pinkRgb},
		// 	labels: {
		//
		// 		style: {colors: [app.color.bodyColor]}
		// 	},
		//   opposite: true,
        //   title: {
        //     // text: 'Expansion Rates',
		// 	style: {color: app.color.warning}
        //   },
        //   min: min_churn_rate,
        //   // max: 4
        // }
		// ],
		tooltip: { },
		// title: { text: 'Resurrected Vs. Retained Rates' }
	};
	var churnedgrowthAreaChart = new ApexCharts(
		document.querySelector('#churnedgrowthChart'),
		churnedgrowthChartOptions
	);
	churnedgrowthAreaChart.render();


var churncontractiondonutChartOptions = {
	chart: {
			height: 100,
			type: 'donut',
		},
		dataLabels: {
			enabled: false

		},
		stroke: {
          show: false
        },
	series: [total_churn, total_contraction],
	labels: ['Churn', 'Contractions'],
	legend: {
          show: false
        },

	colors: ['rgba('+ app.color.themeRgb + ', .35)', 'rgba('+ app.color.themeRgb + ', .95)'],


	};
var churncontractiondonutChart = new ApexCharts(
		document.querySelector('#churncontractiondonut'),
		churncontractiondonutChartOptions
	);
	churncontractiondonutChart.render();


	var positivedonutChartOptions = {
	chart: {
			height: 100,
			type: 'donut',
		},
		dataLabels: {
			enabled: false

		},
		stroke: {
          show: false
        },
	series: [total_new, total_existing],
	labels: ['New', 'Existing'],
	legend: {
          show: false
        },

	colors: [app.color.theme, app.color.warning],


	};
var positivedonutChart = new ApexCharts(
		document.querySelector('#positivedonut'),
		positivedonutChartOptions
	);
	positivedonutChart.render();


var growthanalysisChartOptions = {

	series: [{
          name: 'Quick Ratio',
          type: 'column',
          data: quick_ratio
        }, {
          name: 'Gross Retention',
          type: 'area',
          data: gross_retention
        }, {
          name: 'Net Churn',
          type: 'line',
          data: net_churn
        }],
          chart: {
          height: 350,
          type: 'line',
          stacked: false,
			  zoom: {
            enabled: false
          },
          toolbar: {
            show: false
          }
        },
        stroke: {
          width: [0, 2, 5],
          curve: 'smooth'
        },
        plotOptions: {
          bar: {
            columnWidth: '50%'
          }
        },

        fill: {
          opacity: [0.85, 0.25, 1],
          gradient: {
            inverseColors: false,
            shade: 'light',
            type: "vertical",
            opacityFrom: 0.85,
            opacityTo: 0.55,
            stops: [0, 100, 100, 100]
          }
        },
        labels: cat,
        markers: {
          size: 0
        },
        xaxis: {
          type: 'Months'
        },
        yaxis: {
		labels: {
			formatter: function (val) {
				return val.toFixed(2);
			},
			style: {
					colors: app.color.bodyColor,
					fontSize: '12px',
					fontFamily: app.font.bodyFontFamily,
					fontWeight: app.font.bodyFontWeight,
					cssClass: 'apexcharts-yaxis-label',
				},
		}
          // title: {
          //   text: 'Stats',
          // },
          // min: 0
        },
        tooltip: {
          shared: true,
          intersect: false,
          y: {
            formatter: function (y) {
              if (typeof y !== "undefined") {
                return y.toFixed(2);
              }
              return y;

            }
          }
        }
}

var growthanalysisChart = new ApexCharts(
		document.querySelector('#growthanalysisMixedChart'),
		growthanalysisChartOptions
	);
	growthanalysisChart.render();



};


