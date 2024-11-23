var datePicker = $('#date-range').daterangepicker({
	maxDate: moment(),
	ranges: {
			'Сегодня': [moment(), moment()],
			'Вчера': [moment().subtract(1, 'days'), moment().subtract(1, 'days')],
			'Последние 7 дней': [moment().subtract(6, 'days'), moment()],
			'Последние 30 дней': [moment().subtract(29, 'days'), moment()],
			'Текущий месяц': [moment().startOf('month'), moment().endOf('month')],
			'Последний месяц': [moment().subtract(1, 'month').startOf('month'), moment().subtract(1, 'month').endOf('month')]
	},
	"locale": {
			"format": "DD.MM.YYYY",
			"separator": " - ",
			"applyLabel": "Применить",
			"cancelLabel": "Отменить",
			"fromLabel": "От",
			"toLabel": "До",
			"customRangeLabel": "Произвольно",
			"weekLabel": "W",
			"daysOfWeek": [
					"Вс",
					"Пн",
					"Вт",
					"Ср",
					"Чт",
					"Пт",
					"Сб"
			],
			"monthNames": [
					"Январь",
					"Февраль",
					"Март",
					"Апрель",
					"Май",
					"Июнь",
					"Июль",
					"Август",
					"Сентябрь",
					"Октябрь",
					"Ноябрь",
					"Декабрь"
			],
			"firstDay": 1
	},
	"startDate":  moment().subtract(29, 'days'),
	"endDate": moment().subtract(0, 'days'),
	"opens": "center"
}, function(start, end, label) {
	console.log('New date range selected: ' + start.format('DD.MM.YYYY') + ' to ' + end.format('DD.MM.YYYY') + ' (predefined range: ' + label + ')');
});

Date.prototype.addDays = function(days) {
	var date = new Date(this.valueOf());
	date.setDate(date.getDate() + days);
	return date;
}

function formatDate(date) {

	var dd = date.getDate();
	if (dd < 10) dd = '0' + dd;

	var mm = date.getMonth() + 1;
	if (mm < 10) mm = '0' + mm;


	return date.getFullYear() + '-' + mm + '-' + dd;
}
function getDates(startDate, stopDate) {
	var dateArray = new Array();
	var currentDate = startDate;
	while (currentDate <= stopDate) {
			dateArray.push(formatDate(new Date (currentDate)));
			currentDate = currentDate.addDays(1);
	}
	return dateArray;
}