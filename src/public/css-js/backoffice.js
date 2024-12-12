[...document.querySelectorAll('[data-bs-toggle="tooltip"]')].forEach(e => new bootstrap.Tooltip(e));
[...document.querySelectorAll('[data-bs-toggle="popover"]')].forEach(e => new bootstrap.Popover(e, {
    html: true,
    sanitize: false,
    content: function() {
        return $(`template#template-popover-${e.id}`).html() || "<i>Template not found!</i>";
    },
}));

const $offcanvas = $('#offcanvas');

const flexihtml = {
    hide_column: function(checkbox, uuid) {
        $(`.table-column-${uuid}`).toggle(checkbox.checked);
    },
    toggle_sb2_input: function(selectbox, name) {
        const $col_left = $(`div#div-1-${name}`);
        const $col_right = $(`div#div-2-${name}`);

        if (['is_between', 'is_not_between'].includes($(selectbox).val())) {
            $col_left.removeClass('col-12').addClass('col-6');
            $col_right.removeClass('d-none').addClass('col-6');
            $col_right.find('select, input, textarea').prop('disabled', false);
        } else {
            $col_left.removeClass('col-6').addClass('col-12');
            $col_right.removeClass('col-6').addClass('d-none');
            $col_right.find('select, input, textarea').prop('disabled', true);
        }
    },
    autocomplete: function(input, model, column, callback, sprintf_value, sprintf_label) {
        const $input = $(input).attr('list', `${model}-${column}`);
        const search_value = $input.val().trim();

        var sprintf_value = sprintf_value || function(item) { return item[column]; }
        var sprintf_label = sprintf_label || sprintf_value;
        var $datalist = $(`datalist#${`${model}-${column}`}`);

        if ($datalist.length == 0)
            $datalist = $('<datalist>', {id: `${model}-${column}`}).prependTo($input);

        if (search_value.length >= 3) {
            $datalist.empty();

            return $.ajax({
                type: 'POST',
                url: '/api/autocomplete',
                data: JSON.stringify({'model': model, 'column': column, 'value': search_value}),
                dataType: 'json',
                contentType: 'application/json',
            }).done(function(response) {
                if (response.status) {
                    for (var i in response.items) {
                        var option_value = sprintf_value(response.items[i]);
                        $datalist.append($('<option>', {'value': option_value, 'text': sprintf_label(response.items[i])}));

                        if (option_value == search_value)
                            callback(response.items[i]);
                    }
                } else
                    alert(response.message);
            });
        }
    },
    offcanvas: function(endpoint, data) {
        const $offcanvas_title = $offcanvas.find('h5.offcanvas-title').text('Loading ...');
        const $offcanvas_content = $offcanvas.find('div.offcanvas-body').html('<i class="fa-solid fa-hourglass-half fa-beat"></i> Loading ... ');
        (new bootstrap.Offcanvas($offcanvas)).show();

        $offcanvas.off('shown.bs.offcanvas').on('shown.bs.offcanvas', function(e) {
            return $.ajax({
                type: 'POST',
                url: endpoint,
                data: JSON.stringify(data),
                dataType: 'json',
                contentType: 'application/json',
            }).done(function(response) {
                $offcanvas_title.text(response.title)
                $offcanvas_content.html(response.content);
            }).fail(function(jqXHR, text_status) {
                $offcanvas_title.text(`${jqXHR.status} ${jqXHR.statusText}`);
                $offcanvas_content.html(`Request on "${location.protocol}//${location.host}${endpoint}" was ${jqXHR.statusText} (${jqXHR.status}).`);
            });
        });
    }
};