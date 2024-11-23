(function($) {
	function setChecked(target) {
		const firstSelectOption = $(target).find('.form-control span')
		const selectAllOption = $(target).find('input[value="all"]')[0]
		const allCheckbox = $(target).find("input[type='checkbox']");
		let checked = $(target).find("input[type='checkbox']:checked");
		let checkedLength = checked.filter((i, checkedEl) => $(checkedEl).attr('value') !== 'all').length
		let allCheckboxLength = allCheckbox.length - 1
		let text = $(target).data('text')

		if (checkedLength == allCheckboxLength) {
			firstSelectOption.html(`Выбраны <b>все</b> ${text[1]}`);
			selectAllOption.indeterminate = false
			selectAllOption.checked = true
		} else if (checkedLength) {
			firstSelectOption.html(`Выбрано ${text[0]}: <b>${checkedLength}</b>`);
			selectAllOption.indeterminate = true
			selectAllOption.checked = false
		} else {
			firstSelectOption.html(`Выберите <b>${text[1]}</b> из списка`);
			selectAllOption.indeterminate = false
			selectAllOption.checked = false
		}
		checked = $(target).find("input[type='checkbox']:checked")
		return selectAllOption.checked ? ['all'] : Array.from(checked.map((i, el) =>  $(el).val())) 
	}




	$.fn.checkselect = function(el = ['элементы', 'элементы'],  options = {}) {
		var settings = $.extend( {
			closePopupEvent: (element) => {
					console.log(element.dataChecked);
				},
			changeData: (element, dataPrev, dataCurrent) => {
				console.log()
			},
			allChecked: false,
		}, options);

		this.data('text', el)
		this.prevData = []
		this._temporaryData = []

		this.wrapInner('<div class="checkselect-popup"></div>');
		this.prepend(
			'<div class="checkselect-control">' +
				'<div class="form-control"><span></span></div>' +
				'<div class="checkselect-over"></div>' +
			'</div>'
		);


		if (settings.allChecked) {
			this.find('input[type="checkbox"]').each((i, elem) => {
				elem.checked = true
			})
		}
		var that = this
		this.each(function(){
			that.prevData = that.dataChecked = setChecked(this);
		});
		
		this.find('input[type="checkbox"]').click(function(){
			if (this.getAttribute('value') === 'all') {
				if (this.checked) {
					that.find('input[type="checkbox"]').each(function () { this.checked = true })
				}
				else { that.find('input[type="checkbox"]').each(function () { this.checked = false }) }
			}

			that['dataChecked'] = setChecked($(this).parents('.checkselect'));
		});
 
		this.find('.checkselect-control').on('click', function(){
			$popup = $(this).next();
			// $('.checkselect-popup').not($popup).css('display', 'none');
			if ($popup.is(':hidden')) {
				console.log('open');
				that._temporaryData = that.dataChecked
				$popup.css('display', 'block');
			} else {
				closePopup(that.find('.checkselect-popup'))
			}
		});

		$('html, body').on('click', function(e){
			if ($(e.target).closest('.checkselect').get(0) != that.get(0) && that.find('.checkselect-popup').css('display') == 'block'){
				closePopup(that.find('.checkselect-popup'))
			}
		});

		function closePopup(el) {
			$(el).css('display', 'none')
			if (that._temporaryData != that.dataChecked) {
				that.prevData = that._temporaryData
			}
			console.log('close');
			that.get(0).dispatchEvent(new CustomEvent("checkselect:close",{
				detail: { prevData: that.prevData, dataChecked: that.dataChecked, temporaryData: that._temporaryData}
			}))
			settings.closePopupEvent(that)
		}
		return this
	};
})(jQuery);