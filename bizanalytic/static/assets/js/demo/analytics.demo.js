/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 5.0.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

function newDate(days) {
	return moment().add(days, 'd').format('D MMM');
}

function newDateString(days) {
	return moment().add(days, 'd').format();
}

var chart1, chart2, chart3, chart4, chart5;

var handleRenderChart = function() {
	Chart.defaults.font.family = app.font.bodyFontFamily;
	Chart.defaults.font.size = 12;
	Chart.defaults.color = app.color.bodyColor;
	Chart.defaults.borderColor = app.color.borderColor;
	Chart.defaults.plugins.legend.display = false;
	Chart.defaults.plugins.tooltip.padding = { left: 8, right: 12, top: 8, bottom: 8 };
	Chart.defaults.plugins.tooltip.cornerRadius = 8;
	Chart.defaults.plugins.tooltip.titleMarginBottom = 6;
	Chart.defaults.plugins.tooltip.titleFont.family = app.font.bodyFontFamily;
	Chart.defaults.plugins.tooltip.titleFont.weight = app.font.bodyFontWeight;
	Chart.defaults.plugins.tooltip.footerFont.family = app.font.bodyFontFamily;
	Chart.defaults.plugins.tooltip.displayColors = true;
	Chart.defaults.plugins.tooltip.boxPadding = 6;
	Chart.defaults.scale.grid.color = app.color.borderColor;
	Chart.defaults.scale.beginAtZero = true;
	
	// #chart1
	var ctx = document.getElementById('chart1').getContext('2d');
	chart1 = new Chart(ctx, {
			type: 'line',
			data: {
				labels: ['', '4am', '8am', '12pm', '4pm', '8pm', newDate(1)],
				datasets: [{
					color: app.color.theme,
					backgroundColor: 'transparent',
					borderColor: app.color.theme,
					borderWidth: 2,
					pointBackgroundColor: app.color.bodyBg,
					pointBorderWidth: 2,
					pointRadius: 4,
					pointHoverBackgroundColor: app.color.bodyBg,
					pointHoverBorderColor: app.color.theme,
					pointHoverRadius: 6,
					pointHoverBorderWidth: 2,
					data: [0, 0, 0, 601, 220]
				},{
					color: app.color.secondary,
					backgroundColor: 'transparent',
					borderColor: app.color.secondary,
					borderWidth: 2,
					pointBackgroundColor: app.color.bodyBg,
					pointBorderWidth: 2,
					pointRadius: 4,
					pointHoverBackgroundColor: app.color.bodyBg,
					pointHoverBorderColor: app.color.secondary,
					pointHoverRadius: 6,
					pointHoverBorderWidth: 2,
					data: [0, 0, 0, 500, 120, 0, 0, 0]
				}]
			}
	});
	
	// #chart2
	var ctx2 = document.getElementById('chart2').getContext('2d');
	chart2 = new Chart(ctx2, {
		type: 'line',
		data: {
			labels: ['', '4am', '8am', '12pm', '4pm', '8pm', newDate(1)],
			datasets: [{
				color: app.color.theme,
				backgroundColor: 'transparent',
				borderColor: app.color.theme,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.theme,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 20, 50, 100, 120]
			},{
				color: app.color.secondary,
				backgroundColor: app.color.secondary,
				borderColor: app.color.secondary,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.secondary,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 30, 44, 130, 34, 15, 43, 22]
			}]
		}
});

	// #chart3
	var ctx3 = document.getElementById('chart3').getContext('2d');
	chart3 = new Chart(ctx3, {
		type: 'line',
		data: {
			labels: ['', '4am', '8am', '12pm', '4pm', '8pm', newDate(1)],
			datasets: [{
				color: app.color.indigo,
				backgroundColor: 'transparent',
				borderColor: app.color.indigo,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.indigo,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 5, 18, 9]
			},{
				color: app.color.theme,
				backgroundColor: app.color.theme,
				borderColor: app.color.theme,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.theme,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 10, 26, 13]
			}]
		}
	});

	// #chart4
	var ctx4 = document.getElementById('chart4').getContext('2d');
	chart4 = new Chart(ctx4, {
		type: 'line',
		data: {
			labels: ['', '4am', '8am', '12pm', '4pm', '8pm', newDate(1)],
			datasets: [{
				color: app.color.theme,
				backgroundColor: 'transparent',
				borderColor: app.color.theme,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.theme,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 0, 24, 39]
			},{
				color: app.color.secondary,
				backgroundColor: app.color.secondary,
				borderColor: app.color.secondary,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.secondary,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 0, 28, 35, 23, 0, 0]
			}]
		}
	});
	
	// #chart5
	var ctx5 = document.getElementById('chart5').getContext('2d');
	chart5 = new Chart(ctx5, {
		type: 'line',
		data: {
			labels: ['', '4am', '8am', '12pm', '4pm', '8pm', newDate(1)],
			datasets: [{
				color: app.color.theme,
				backgroundColor: 'transparent',
				borderColor: app.color.theme,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.theme,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 0, 12, 5]
			},{
				color: app.color.secondary,
				backgroundColor: app.color.secondary,
				borderColor: app.color.secondary,
				borderWidth: 2,
				pointBackgroundColor: app.color.bodyBg,
				pointBorderWidth: 2,
				pointRadius: 4,
				pointHoverBackgroundColor: app.color.bodyBg,
				pointHoverBorderColor: app.color.secondary,
				pointHoverRadius: 6,
				pointHoverBorderWidth: 2,
				data: [0, 0, 0, 10, 4, 2, 0, 0]
			}]
		}
	});
}

var handleDaterangepicker = function() {
	$('[data-id="prev-date"]').html(moment().add(-1, 'd').format('D MMM YYYY'));
	$('[data-id="today-date"]').html(moment().format('D MMM YYYY'));
	
	$('#daterangepicker').daterangepicker({
    opens: 'right',
    format: 'MM/DD/YYYY',
    separator: ' to ',
    startDate: moment(),
    endDate: moment(),
    maxDate: moment()
  });
};


/* Controller
------------------------------------------------ */
$(document).ready(function() {
	handleRenderChart();
	handleDaterangepicker();
	
	$(document).on('theme-reload', function() {
		chart1.destroy();
		chart2.destroy();
		chart3.destroy();
		chart4.destroy();
		chart5.destroy();
		
		$('#chart1, #chart2, #chart3, #chart4, #chart5').removeAttr('width');
		handleRenderChart();
	});
});