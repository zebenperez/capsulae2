
// side menu toggle
function expandMenu(element){
	let sidebar = document.getElementById("sidebar");
	sidebar.classList.toggle("expanded");
	sidebar.classList.toggle("closed");
	console.log("end");
}

//Dictiionay with delegator selector and event handler
const _CLK_DELEGATORS = {
	'.menu-btn': expandMenu,
}

// Event Delegation
document.addEventListener('click', function(e){
	for (let selector in _CLK_DELEGATORS)
	{
		let delegate = e.target.closest(selector)
		if(delegate){
			_CLK_DELEGATORS[selector](delegate);
			e.preventDefault();
		}
	}
});



// Update side menu when spa-content is loaded
document.addEventListener('loadedcontent', function(e){
	let url = e.detail.url.pathname;
	console.log(url);
	let activeItem = document.querySelector(`.menu-item[data-section='${url}']`)
	if (activeItem){
		 let currActive = document.querySelector(".menu-item.active")
		 if(currActive) currActive.classList.remove("active");
		activeItem.classList.add("active");
	}
});
//detects when sigle page content is loaded to update side-menu
$('body').on('loadedcontent', ()=>{
	url = $('#ajax-container').attr('url');
	url_parts = url.split("?")[0].split("/");

	section = (url == "/events/") ? "dashboard" : url_parts.pop() || url_parts.pop();
	$('.menu-item.active').removeClass("active")
	$(`.menu-item[data-section='${section}']`).addClass("active");
});
