
function calcula_cambio()
{
    try {
        entrega = parseFloat( $('#entrega').val());
        total_str = $('#total_a_pagar').html();
        total = parseFloat(total_str.replace(',','.'));
        if (!isNaN(entrega - total)) {
            $('#change_returned').html((entrega - total).toFixed(2));
        }
        url = $('#entrega').data("url");
        invoice_id = $('#entrega').data("invoice");
        diff = (entrega - total).toFixed(2);
        ajaxGet(url, {'invoice_id': invoice_id, 'paid': entrega, 'diff': diff}, "", "");
    } catch (error) {};
}
