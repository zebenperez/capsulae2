/** Global Variables */
// Almacena las puntuaciones insertadas en cada fila de la tabla.
const RISK_SCORES = [0,0,0,0,0,0,0,0];


/**
 * Obtiene el valor introducido en el elemento pasado como parametro
 * y lo inserta en el array de puntuaciones de riestos.
 *
 * @param {Object} el - Elemento input que es modificado.
 *
 * */
function calculateRisk(el){

	let index = el.closest(".risk-table-row").dataset.index;
	let value = parseInt(el.value);
	if (!isNaN(value)){
		RISK_SCORES[index] = value;
	}else{
		RISK_SCORES[index] = 0;
	}
}


/**
 *	Moverá el check de la tabla de riesgos, a la celda
 *	cuya puntuación coincida con la calculada en el formulario
 * */
function markRiskScale(){
	let totalScore = RISK_SCORES.reduce((total, curr)=> total += curr );
	totalScore = (totalScore < 1) ? 1 : (totalScore > 8) ? 8 : totalScore;
	let iconElement = document.getElementById("check-icon");
	let cell = document.querySelector(`.meter-row .metric-${totalScore}`);
	cell.appendChild(iconElement)
}


/**
 *  El evento keyUp esta delegado al document.
 */
document.addEventListener("keyup", (ev)=>{
	let el = ev.srcElement;
	if (el.matches(".risk-table-row input.print-input"))
	{
		calculateRisk(el);
		markRiskScale();
	}
});
