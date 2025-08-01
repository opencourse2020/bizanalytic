/*
Template Name: HUD - Responsive Bootstrap 5 Admin Template
Version: 5.0.0
Author: Sean Ngu
Website: http://www.seantheme.com/hud/
*/

import { createPopup } from 'https://unpkg.com/@picmo/popup-picker@latest/dist/index.js?module';

var handleRenderPickmo = function() {
	const selectionContainer = document.querySelector('#selection-outer');
  const emoji = document.querySelector('#selection-emoji');
  const name = document.querySelector('#selection-name');
  const trigger = document.querySelector('#trigger');

  const picker = createPopup({}, {
    referenceElement: trigger,
    triggerElement: trigger,
    position: 'right-end'
  });

  trigger.addEventListener('click', () => {
    picker.toggle();
  });

  picker.addEventListener('emoji:select', (selection) => {
    $('#input').val($('#input').val() + selection.emoji)

    selectionContainer.classList.remove('empty');
  });
};

var handleChatScrollBottom = function() {
  var elm = document.querySelector('.messenger-content-body [data-scrollbar="true"]');
	elm.scrollTop = elm.scrollHeight - elm.clientHeight;
	
	var elm = document.querySelector('.messenger-content-body');
	elm.classList.remove('invisible');
};

var handleMobileMessengerToggler = function() {
	$(document).on('click', '[data-toggle="messenger-content"]', function(e) {
		e.preventDefault();
		
		$('.messenger').toggleClass('messenger-content-toggled');
	});
};


$(document).ready(function() {
  handleRenderPickmo();
  handleChatScrollBottom();
  handleMobileMessengerToggler();
});