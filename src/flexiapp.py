import uuid
import math
import json
import hashlib
import pathlib

from typing import Any, Callable, Optional, Union
from sqlalchemy import (
    Engine,
    Column,
    Integer,
    Select,
    inspect,
    not_,
    null,
    text,
    func,
)
from sqlalchemy.orm import (
    Session,
    DeclarativeBase,
    RelationshipDirection,
    Mapped,
    mapped_column,
)
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.relationships import _RelationshipDeclared

FLEXIAPP_PATH = pathlib.Path(__file__).resolve().parent


def uuid_text(to_encode: str) -> str:
    return str(uuid.UUID(hex=hashlib.md5(str(to_encode).encode("UTF-8")).hexdigest()))


def short_uuid_text(to_encode: str) -> str:
    return uuid_text(to_encode)[0:8]


def is_column_bool(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in [
        "bool",
        "boolean",
        "matchtype",
    ]


def is_column_uuid(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["uuid"]


def is_column_text(column: InstrumentedAttribute) -> bool:
    return is_column_uuid(column) or column.type.__class__.__name__.lower() in [
        "text",
        "str",
        "string",
        "autostring",
        "char",
        "nchar",
        "varchar",
        "nvarchar",
        "blob",
        "clob",
        "unicode",
        "unicodetext",
    ]


def is_column_int(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in [
        "int",
        "integer",
        "numeric",
        "smallint",
        "smallinteger",
        "bigint",
        "biginteger",
    ]


def is_column_float(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in [
        "real",
        "float",
        "decimal",
        "double",
        "double_precision",
    ]


def is_column_numeric(column: InstrumentedAttribute) -> bool:
    return is_column_int(column) or is_column_float(column)


def is_column_binary(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in [
        "binary",
        "varbinary",
        "largebinary",
    ]


def is_column_datetime(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["datetime", "date", "time"]


def is_column_enum(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["enum"]


def is_column_json(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["json"]


def is_column_list(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["list", "array"]


def is_column_interval(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["interval"]


def is_column_timestamp(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["timestamp"]


def is_column_geometry(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["geometry"]


def is_column_nullable(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["nulltype"]


def is_column_schema(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["schematype"]


def is_column_pickle(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["pickletype"]


def is_column_expression_lookup(column: InstrumentedAttribute) -> bool:
    return column.type.__class__.__name__.lower() in ["hasexpressionlookup"]


def deep_access(
    this: object,
    dotted_name: str,
    default_value: Any = None,
    callback: Optional[Callable[[Any], Any]] = None,
) -> Any:
    value = default_value

    for name in dotted_name.split("."):
        if value := getattr(this, name, None):
            if isinstance(value, object):
                this = value
        else:
            return default_value

    if callable(callback):
        return callback(value)

    return value


def html_encode(to_encode: str) -> str:
    for subject, replacement in {"&": "&amp;", '"': "&quot;", "'": "&#039;", "<": "&lt;", ">": "&gt;"}.items():
        to_encode = to_encode.replace(subject, replacement)

    return to_encode.strip()


def flatten_attributes(attributes: dict) -> str:
    html = ""

    for name, value in attributes.items():
        if value == "":
            continue

        if isinstance(value, (list, tuple, dict)):
            value = json.dumps(value)

        if isinstance(value, bool):
            value = "1" if value is True else "0"

        html += f'{name}="{html_encode(str(value))}" '

    return html.strip()


class ModelT:
    def __init__(self):
        self._properties: dict = {}

    def __getitem__(self, key: str) -> Any | None:
        if key is Ellipsis:
            return self._properties

        return self._properties.get(key)

    def __setitem__(self, key: str, value: int | float | str):
        if key is Ellipsis and isinstance(value, dict):
            self._properties.update(value)
        elif key is not Ellipsis:
            self._properties[key] = value


class XHtmlElement:
    def __init__(self, attributes: dict[str, str] = {}):
        self.attributes: dict[str, str] = {}
        self.attributes.update(attributes)
        self.previous_xhtml: list[XHtmlElement] = []

    def __add__(self, this: "XHtmlElement") -> "XHtmlElement":
        if isinstance(this, XHtmlElement):
            this.previous_xhtml.extend(self.previous_xhtml)
            this.previous_xhtml.append(self)

        return this

    def __getitem__(self, key: str) -> Any | None:
        if key is Ellipsis:
            return self.attributes

        return self.attributes.get(key)

    def __setitem__(self, key: str, value: int | float | str):
        if key is Ellipsis and isinstance(value, dict):
            self.attributes.update(value)
        elif key is not Ellipsis:
            self.attributes[key] = value

    def template(self) -> str:
        return ""

    def previous_template(self) -> str:
        html = ""

        for item in self.previous_xhtml:
            html += item.template()

        return html

    def content(self) -> str:
        return self.previous_template() + self.template()


class HtmlElement(XHtmlElement):
    def __init__(self, html: str | XHtmlElement, *, tag: str = "div", attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self.tag = tag
        self.html = html

    def template(self) -> str:
        if isinstance(html := self.html, XHtmlElement):
            html = self.html.template()

        return f"<{(tag := self.tag.lower())} {flatten_attributes(self.attributes)}>{html}</{tag}>"


class FormElement(XHtmlElement):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self.attributes["id"] = self.id = f"fx-{short_uuid_text(name)}"
        self.attributes["name"] = self.name = name
        self.attributes["value"] = value


class Input(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, type: str = "text", attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self.attributes["type"] = type
        self.attributes["class"] = "form-control"

    def template(self) -> str:
        return f"""
            <input {flatten_attributes(self.attributes)} />
        """


class Date(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="date", attributes=attributes)


class Datetime(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="datetime", attributes=attributes)


class Time(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="time", attributes=attributes)


class Hidden(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="hidden", attributes=attributes)


class Password(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="password", attributes=attributes)


class Int(Input):
    def __init__(self, name: str, value: Union[int] = "", *, step: int = 1, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="number", attributes=attributes)
        self.attributes["step"] = step


class Float(Input):
    def __init__(self, name: str, value: Union[float] = "", *, step: int | float = 0.01, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="number", attributes=attributes)
        self.attributes["step"] = step


class Text(Input):
    def __init__(self, name: str, value: int | float | str = "", *, data: str | list[str] = None, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="text", attributes=attributes)

        if data and not isinstance(data, (str, list)):
            raise ValueError("Invalid data list")
    
        self.data = data
        self.attributes["list"] = self.datalist_id = f"datalist-{self.id}"

    def template(self) -> str:
        if self.data is None:
            return super().template()

        options = ""

        if isinstance(self.data, list):
            for value in self.data:
                options += f"<option {flatten_attributes({'value': value})} />"
        else:
            self.attributes["oninput"] = f"""
                (function(input) {{
                    const $input = $(input);
                    const $datalist = $("datalist#{self.datalist_id}");
                    const search_value = $input.val().trim();

                    if (search_value.length >= 3) {{
                        $datalist.empty();

                        return $.ajax({{
                            type: "POST",
                            url: "{self.data}",
                            data: JSON.stringify({{"query": search_value}}),
                            dataType: "json",
                            contentType: "application/json",
                        }}).done(function(response) {{
                            if (response.status) {{
                                $datalist.empty();
                            
                                for (var i in response.items) {{
                                    $datalist.append($('<option>', {{"value": response.items[i]}}));
                                }}
                            }} else {{
                                alert(response.message);
                            }}
                        }});
                    }}
                }})(this);
            """

        return f"""
            <datalist id="{self.datalist_id}">
                {options}
            </datalist>
            {super().template()}
        """


class File(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="file", attributes=attributes)


class Range(Input):
    def __init__(self, name: str, value: int | float | str = "", *, min_value: int | float = 0, max_value: int | float = 100, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="range", attributes=attributes)
        self.attributes["min"] = min_value
        self.attributes["max"] = max_value
        self.attributes["class"] = "form-range"


class Radio(Input):
    def __init__(self, name: str, value: int | float | str = "", *, label: str, checked: bool = False, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="radio", attributes=attributes)
        self.label = label
        self.attributes["id"] = f"rd-{self.attributes['id']}-{short_uuid_text(value)}"
        self.attributes["class"] = "form-check-input"

        if checked:
            self.attributes["checked"] = 1

    def template(self) -> str:
        return f'''
            <div class="form-check">
                <input {flatten_attributes(self.attributes)} />
                <label class="form-check-label" for="{self.attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class SwitchRadio(Radio):
    def template(self) -> str:
        return f'''
            <div class="form-check form-switch">
                <input {flatten_attributes(self.attributes)} />
                <label class="form-check-label" for="{self.attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class Checkbox(Input):
    def __init__(self, name: str, value: int | float | str = "", *, label: str, checked: bool = False, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="checkbox", attributes=attributes)
        self.label = label
        self.attributes["class"] = "form-check-input"

        if checked:
            self.attributes["checked"] = 1

    def template(self) -> str:
        return f'''
            <div class="form-check">
                <input {flatten_attributes(self.attributes)} />
                <label class="form-check-label" for="{self.attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class SwitchCheckbox(Checkbox):
    def template(self) -> str:
        return f'''
            <div class="form-check form-switch">
                <input {flatten_attributes(self.attributes)} />
                <label class="form-check-label" for="{self.attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class Button(Input):
    def __init__(self, name: str, *, label: str = "Submit", type: str = "submit", value: int | float | str = "", attributes: dict[str, str] = {}):
        super().__init__(name, value, type=type, attributes=attributes)
        self.label = label
        self.attributes["class"] = "btn btn-primary"

    def template(self) -> str:
        return f"""
            <button {flatten_attributes(self.attributes)}>{self.label}</button>
        """


class Textarea(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self.attributes["class"] = "form-control"

    def template(self) -> str:
        value = ""

        if "value" in self.attributes:
            value = self.attributes.pop("value")

        return f"""
            <textarea {flatten_attributes(self.attributes)}>{value}</textarea>
        """


class Selectbox(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, options: dict[str, str], attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self.options = options
        self.attributes["class"] = "form-select"

    def template(self) -> str:
        values = []

        if "value" in self.attributes:
            values = self.attributes.pop("value")

        if not isinstance(values, list):
            values = [str(values) or ""]

        html = f"""
            <select {flatten_attributes(self.attributes)}>
        """

        for item_value, item_label in self.options.items():
            tmp_attributes = {"value": item_value}

            if item_value in values:
                tmp_attributes["selected"] = 1

            html += f"""
                <option {flatten_attributes(tmp_attributes)}>{html_encode(item_label)}</option>
            """

        html += """
            </select>
        """

        return html


class Searchbox(Selectbox):
    def __init__(self, name: str, value: int | float | str = "", *, endpoint: str, options: dict[str, str] = {}, attributes={}):
        super().__init__(name, value, options=options, attributes=attributes)
        self.endpoint = endpoint

    def template(self):
        popover_button = Button(f"popover-button-{self.name}", label='<i class="fa-solid fa-ellipsis"></i>', type="button")
        popover_button["class"] = "btn btn-secondary"
        popover_button["data-bs-toggle"] = "popover"
        popover_button["data-bs-placement"] = "top"
        searchbox = Text(f"searchbox-{self.name}")
        pull_button = Button(f"pull-button-{self.name}", label='<i class="fa-solid fa-magnifying-glass"></i>', type="button")
        pull_button["onclick"] = f"""
            (function(button) {{
                const $button = $(button);
                const $input = $("select#{self.id}");
                const $searchbox = $("input#{searchbox.id}");
                const $popover_button = $("button#{popover_button.id}");
                
                $button.prop("disabled", true).html('<i class="fa-solid fa-spinner fa-spin"></i>');

                return $.ajax({{
                    type: "POST",
                    url: "{self.endpoint}",
                    data: JSON.stringify({{"query": $searchbox.val()}}),
                    dataType: "json",
                    contentType: "application/json",
                }}).done(function(response) {{
                    $button.prop("disabled", false).html('<i class="fa-solid fa-magnifying-glass"></i>');
                    $popover_button.click();

                    if (response.status) {{
                        $input.empty();
                    
                        for (var i in response.items) {{
                            $input.append($("<option>", {{"value": i, "text": response.items[i]}}));
                        }}
                    }} else {{
                        alert(response.message);
                    }}
                }});
            }})(this);
        """

        return f"""
            <template id="template-popover-{popover_button.id}">
                <div class="input-group">
                    {searchbox.content()}
                    {pull_button.content()}
                </div>
            </template>
            <div class="input-group">
                {popover_button.content()}
                {super().template()}
            </div>
        """


class Frame(XHtmlElement):
    def __init__(self, element: FormElement, *, width: str = "312px", height: str = "162px", attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self.element = element
        self.attributes["id"] = self.id = f"fm-{self.element.id}"
        self.attributes["src"] = self.element["value"]
        self.attributes["class"] = "img-fluid border border-2 p-1"
        self.attributes["width"] = width
        self.attributes["height"] = height


class PhotoFrame(Frame):
    def template(self):
        self.element["onchange"] = f"""
            (function(input) {{
                $("img#{self.id}").attr("src", $(input).val());
            }})(this);
        """

        return f"""
            <div class="mb-2">
                <img {flatten_attributes(self.attributes)} />
            </div>
            {self.element.content()}    
        """


class VideoFrame(Frame):
    def __init__(self, element: FormElement, *, width: str = "312px", height: str = "162px", attributes: dict[str, str] = {}):
        super().__init__(element, width=width, height=height, attributes=attributes)
        self.attributes["controls"] = "controls"

    def template(self):
        self.element["onchange"] = f"""
            (function(input) {{
                $("video#{self.id}").attr("src", $(input).val());
            }})(this);
        """

        return f"""
            <div class="mb-2">
                <video {flatten_attributes(self.attributes)}>
                    Your browser does not support the video tag.
                </video>
            </div>
            {self.element.content()}    
        """


class Listbox(FormElement):
    def __init__(self, name: str, *, element: FormElement, list_items: list[str] = [], attributes: dict[str, str] = {}):
        tmp_element = element.element if isinstance(element, Frame) else element

        if not isinstance(tmp_element, (Int, Float, Text, Textarea, Selectbox, Searchbox)):
            raise ValueError(f"Param 'element' must be Int, Float, Text, Textarea, Selectbox or Searchbox. Got: {type(tmp_element)}.")

        super().__init__(name, attributes=attributes)
        self.element = element
        self.list_items = list_items

    def item_template(self, item: str, classname: str = "") -> str:
        tmp_element = self.element.element if isinstance(self.element, Frame) else self.element

        return f"""
            <li class="d-block flexilist-ul-item">
                &rarrhk; <a 
                    href="javascript:void(0)"
                    class="flexilist-ul-item-edit {classname}"
                    onclick="{
            html_encode(f'''
                        (function(item) {{
                            $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                                const $item = $(e);

                                if ($item.is(":empty"))
                                    $item.parent("li.flexilist-ul-item").remove();
                            }});

                            const $item = $(item);

                            if (!$item.parent("li.flexilist-ul-item").hasClass("is-deleted")) {{
                                const $input = $("#flexilist-input-{self.id}").find("#{tmp_element.id}");
                                const $items = $("ul#flexilist-ul-{self.id} a.flexilist-ul-item-edit");
                                const $button = $("a#flexilist-{self.id}-button");
                            
                                $items.removeClass("is-connected"); 
                                $item.addClass("is-connected");
                                $input.val($item.text()).trigger("change").focus();
                                $button.text("disconnect");
                            }}
                        }})(this);
                    ''')
        }">{item}</a>
                <a 
                    href="javascript:void(0)"
                    class="flexilist-ul-item-action"
                    is-deleted="0"
                    onclick="{
            html_encode('''
                        (function(button) {{
                            const $button = $(button);
                            
                            if ($button.attr("is-deleted") == "0") {{
                                $button.attr("is-deleted", "1");
                                $button.html('&ndash; <i class="fa-solid fa-trash-can-arrow-up"></i>');
                                $button.parent("li").addClass("is-deleted");
                            }} else {{
                                $button.attr("is-deleted", "0");
                                $button.html('&ndash; <i class="fa-solid fa-trash"></i>');
                                $button.parent("li").removeClass("is-deleted");
                            }}
                        }})(this);
                    ''')
        }">&ndash; <i class="fa-solid fa-trash"></i></a>
            </li>
        """

    def template(self) -> str:
        tmp_element = self.element.element if isinstance(self.element, Frame) else self.element
        tmp_element["onblur"] = f"""
            (function(input) {{
                const $connection = $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit.is-connected");

                if ($connection.length == 0) {{
                    $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                        const $item = $(e);

                        if ($item.is(":empty"))
                            $item.parent("li.flexilist-ul-item").remove();
                    }});
                }}
            }})(this);
        """
        tmp_element["oninput"] = f"""
            (function(input) {{
                const $input = $(input);
                const $connection = $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit.is-connected");

                if ($connection.length > 0) {{
                    $connection.text($input.val());
                }}
            }})(this);
        """

        html = f"""
            <div id="flexilist-{self.id}" class="flexiapp flexlist">
                <div id="flexilist-input-{self.id}">
                    {self.element.content()}
                </div>
                <div class="float-end">
                    <a 
                        id="flexilist-{self.id}-button"
                        class="mt-2"
                        href="javascript:void(0)"
                        onclick="{
            html_encode(f'''
                            (function(button) {{
                                const $button = $(button);
                                const $input = $("#flexilist-input-{self.id}").find("#{tmp_element.id}");
                                const $listbox = $("ul#flexilist-ul-{self.id}");
                                const $connection = $listbox.find(".flexilist-ul-item-edit.is-connected");

                                if ($connection.length > 0) {{
                                    $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                                        const $item = $(e);

                                        if ($item.is(":empty"))
                                            $item.parent("li.flexilist-ul-item").remove();
                                    }});

                                    $connection.removeClass("is-connected");
                                    $input.val("").focus();
                                    $button.text("add");
                                }} else {{
                                    const $item = $(`{self.item_template("", "is-connected").strip()}`);

                                    $item.find(".flexilist-ul-item-edit").text($input.val());
                                    $listbox.append($item);
                                    $listbox.scrollTop($listbox.prop("scrollHeight"));
                                    $input.focus();
                                    $button.text("disconnect");
                                }}
                            }})(this);
                        ''')
        }">add</a>
                </div>
                <div class="clearfix"></div>
                <ul 
                    name="{self.name}"
                    id="flexilist-ul-{self.id}"
                    class="flexilist-ul mt-2 ps-0">
        """

        for item in self.list_items:
            html += self.item_template(html_encode(str(item)))

        html += """
                </ul>
            </div>
        """

        return html


class Dictbox(FormElement):
    def __init__(self, name: str, *, elements: dict[str, FormElement], list_items: list[dict[str, str]] = [], attributes: dict[str, str] = {}):
        for i, element in elements.items():
            tmp_element = element.element if isinstance(element, Frame) else element

            if not isinstance(tmp_element, (Int, Float, Text, Textarea, Selectbox, Searchbox)):
                raise ValueError(f"Param 'elements' must be a dict of Int, Float, Text, Textarea, Selectbox or Searchbox. Got: {type(tmp_element)} (param: {i}).")

        super().__init__(name, attributes=attributes)
        self.elements = elements
        self.list_items = list_items

    def item_template(self, item: dict, classname: str = "") -> str:
        content = ""

        for label, element in self.elements.items():
            tmp_element = element.element if isinstance(element, Frame) else element

            content += f"""
                <li class="mb-0 pb-0 d-block">
                    <a
                        name="{tmp_element.name}"
                        href="javascript:void(0)"
                        onclick="{
                html_encode(f'''
                            (function(item) {{
                                $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                                    const $item = $(e);
                                    var content = "";

                                    $item.find("a span").each(function(j, f) {{
                                        content += $(f).text();
                                    }});

                                    if (content.trim() == "") {{
                                        $item.parent("li.flexilist-ul-item").remove();
                                    }}  
                                }});

                                const $item = $(item);
                                const $item_dict = $item.parents(".flexilist-ul-item-edit:first");

                                if (!$item_dict.parent(".flexilist-ul-item").hasClass("is-deleted")) {{
                                    const $button = $("#flexilist-{self.id}-button");

                                    $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").removeClass("is-connected"); 
                                    $item_dict.addClass("is-connected");
                                    $item_dict.find("li a").each(function(i, e) {{
                                        const $a = $(e);
                                        const $input = $("#flexilist-input-{self.id}").find("[name=" + $a.attr("name") + "]");

                                        $input.val($a.find("span").text()).trigger("change");

                                        if ($item.attr("name") == $a.attr("name"))
                                            $input.focus();
                                    }});
                                    $button.text("disconnect");
                                }}
                            }})(this);
                        ''')
            }">
                            <b>{label}</b>: 
                            <span>{html_encode(str(item.get(tmp_element.name, "")))}</span>
                    </a>
                </li>
            """

        return f"""
            <li class="d-block flexilist-ul-item">
                &#123;
                <div class="flexilist-ul-item-edit {classname}">
                    <ul class="flexilist-ul mt-0 ps-3">
                        {content}
                    </ul>
                </div>
                &#125;, <a 
                    href="javascript:void(0)"
                    class="flexilist-ul-item-action"
                    is-deleted="0"
                    onclick="{
            html_encode('''
                        (function(button) {{
                            const $button = $(button);
                            
                            if ($button.attr("is-deleted") == "0") {{
                                $button.attr("is-deleted", "1");
                                $button.html('&ndash; <i class="fa-solid fa-trash-can-arrow-up"></i>');
                                $button.parent("li").addClass("is-deleted");
                            }} else {{
                                $button.attr("is-deleted", "0");
                                $button.html('&ndash; <i class="fa-solid fa-trash"></i>');
                                $button.parent("li").removeClass("is-deleted");
                            }}
                        }})(this);
                    ''')
        }">&ndash; <i class="fa-solid fa-trash"></i></a>
            </li>
        """

    def template(self) -> str:
        content = ""

        for label, element in self.elements.items():
            tmp_element = element.element if isinstance(element, Frame) else element
            tmp_element["onblur"] = f"""
                (function(input) {{
                    const $connection = $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit.is-connected");

                    if ($connection.length == 0) {{
                        (function() {{
                            $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                                const $item = $(e);
                                var content = "";

                                $item.find("a span").each(function(j, f) {{
                                    content += $(f).text();
                                }});

                                if (content.trim() == "") {{
                                    $item.parent("li.flexilist-ul-item").remove();
                                }}  
                            }});
                        }})();
                    }}
                }})(this);
            """
            tmp_element["oninput"] = f"""
                (function(input) {{
                    const $input = $(input);

                    $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit.is-connected a").each(function(i, e) {{
                        const $a = $(e);

                        if ($a.attr("name") == $input.attr("name"))
                            $a.find("span").text($input.val());
                    }});
                }})(this);
            """
            content += (FormGroup(element, label=label, colsize=8)).content()

        html = f"""
            <div id="flexilist-{self.id}" class="flexiapp flexlist">
                <div id="flexilist-input-{self.id}">
                    {content}
                </div>
                <div class="float-end">
                    <a 
                        id="flexilist-{self.id}-button"
                        class="mt-2"
                        href="javascript:void(0)"
                        onclick="{
            html_encode(f'''
                            (function(button) {{
                                const $button = $(button);
                                const $listbox = $("ul#flexilist-ul-{self.id}");
                                const $inputbox = $("#flexilist-input-{self.id}");
                                const $connection = $listbox.find(".flexilist-ul-item-edit.is-connected");

                                if ($connection.length > 0) {{
                                    $("ul#flexilist-ul-{self.id} .flexilist-ul-item-edit").each(function(i, e) {{
                                        const $item = $(e);
                                        var content = "";

                                        $item.find("a span").each(function(j, f) {{
                                            content += $(f).text();
                                        }});

                                        if (content.trim() == "") {{
                                            $item.parent("li.flexilist-ul-item").remove();
                                        }}  
                                    }});

                                    $connection.removeClass("is-connected");
                                    $inputbox.find("input, textarea, select").val("");
                                    $button.text("add");
                                }} else {{
                                    const $item = $(`{self.item_template({}, "is-connected").strip()}`);

                                    $item.find(".flexilist-ul-item-edit a").each(function(i, e) {{
                                        const $a = $(e);
                                        const $input = $inputbox.find("[name=" + $a.attr("name") + "]");
                                        
                                        $a.find("span").text($input.val());
                                    }});
                                    $listbox.append($item);
                                    $listbox.scrollTop($listbox.prop("scrollHeight"));
                                    $inputbox.find("input, textarea, select").focus();
                                    $button.text("disconnect");
                                }}
                            }})(this);
                        ''')
        }">add</a>
                </div>
                <div class="clearfix"></div>
                <ul 
                    name="{self.name}"
                    id="flexilist-ul-{self.id}"
                    class="flexilist-ul tallest mt-2 ps-0">
        """

        for item in self.list_items:
            html += self.item_template(item)

        html += """
                </ul>
            </div>
        """

        return html


class FormGroup(XHtmlElement):
    def __init__(self, element: FormElement, *, label: str, colsize: int = 12, help_text: str = "", attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self.element = element
        self.label = label
        self.colsize = colsize
        self.help_text = help_text
        self.attributes["id"] = self.id = f"fx-group-{short_uuid_text(label)}"
        self.attributes["class"] = "form-group fx-group"

    def template(self) -> str:
        if isinstance(self.element, Hidden):
            return self.element.content()

        if self.colsize < 12:
            return f"""
                <div {flatten_attributes(self.attributes)}>
                    <div class="row">
                        <label class="col-form-label col-{12 - self.colsize}">{html_encode(self.label)}</label>
                        <div class="col-{self.colsize}">
                            {self.element.content()}
                            <small class="form-text text-muted">{html_encode(self.help_text)}</small>
                        </div>
                    </div>
                </div>
            """
        else:
            return f"""
                <div {flatten_attributes(self.attributes)}>
                    <label class="form-label">{html_encode(self.label)}</label>
                    {self.element.content()}
                    <small class="form-text text-muted">{html_encode(self.help_text)}</small>
                </div>
            """


class FloatingLabel(FormGroup):
    def template(self) -> str:
        return f"""
            <div {flatten_attributes(self.attributes)}>
                <div class="form-floating">
                    {self.element.content()}
                    <label class="form-label" for="{self.element.id}">{html_encode(self.label)}</label>
                </div>
                <small class="form-text text-muted">{html_encode(self.help_text)}</small>
            </div>
        """


class Form(XHtmlElement):
    class e:
        Input: FormElement = Input
        Date: FormElement = Date
        Time: FormElement = Time
        Datetime: FormElement = Datetime
        Hidden: FormElement = Hidden
        Password: FormElement = Password
        Int: FormElement = Int
        Float: FormElement = Float
        File: FormElement = File
        Range: FormElement = Range
        Radio: FormElement = Radio
        SwitchRadio: FormElement = SwitchRadio
        Checkbox: FormElement = Checkbox
        SwitchCheckbox: FormElement = SwitchCheckbox
        Button: FormElement = Button
        Text: FormElement = Text
        Textarea: FormElement = Textarea
        Selectbox: FormElement = Selectbox
        Listbox: FormElement = Listbox
        Dictbox: FormElement = Dictbox
        Searchbox: FormElement = Searchbox
        FormGroup: XHtmlElement = FormGroup
        FloatingLabel: XHtmlElement = FloatingLabel

    def template(self) -> str:
        return super().template()

    def add_form_group(self):
        pass

    def add_floating_label(self):
        pass


class Table(XHtmlElement):
    pass


class TableFilter(XHtmlElement):
    pass


class Fleximodel(DeclarativeBase):
    __SQLALCHEMY_ENGINE__: Engine = False

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    def __repr__(self) -> str:
        return f"ID: {self.id}"

    def get(
        self,
        dotted_name: str,
        default_value: Any = None,
        callback: Optional[Callable[[Any], Any]] = None,
    ) -> Optional[Any]:
        return deep_access(self, dotted_name, default_value, callback)


class T(object):
    def __init__(self, properties: dict = {}):
        self.content(properties)
        self.__properties__ = properties
        self.__total_items_count__: int = -1

    def __getitem__(self, key):
        if key is Ellipsis:
            return "Accessing all elements"
        else:
            return f"Accessing element {key}"

    def content(self, properties: dict) -> "T":
        for name, value in properties.items():
            if isinstance(value, dict):
                setattr(self, name, T(value))
            else:
                setattr(self, name, value)

        return self

    def count(self) -> int:
        return self.__total_items_count__

    def props(self) -> int:
        return self.__properties__

    def get(
        self,
        dotted_name: str,
        default_value: Any = None,
        callback: Optional[Callable[[Any], Any]] = None,
    ) -> Any:
        return deep_access(self, dotted_name, default_value, callback)

    def set(self, dotted_name: str, value: Any, raise_exception: bool = True) -> bool:
        this = self
        last_name = None

        for name in dotted_name.split("."):
            if old_value := getattr(this, name, None):
                last_name = name

                if isinstance(old_value, object) and type(old_value).__name__ not in dir(__builtins__):
                    this = old_value

        if last_name is not None:
            try:
                return setattr(this, last_name, value) or True
            except Exception as e:
                if raise_exception:
                    raise e

                return False


class Flexihtml:
    @property
    def logo_image(self) -> str:
        return self.__logo_image

    @property
    def title(self) -> str:
        return self.__title

    @property
    def description(self) -> str:
        return self.__description

    @property
    def breadcrumb(self) -> "Flexihtml.Breadcrumb":
        return self.__breadcrumb

    @property
    def tabs(self) -> "Flexihtml.Tabs":
        return self.__tabs

    @property
    def form(self) -> "Flexihtml.Form":
        return self.__form

    @property
    def table(self) -> "Flexihtml.Table":
        return self.__table

    @property
    def searchbox(self) -> "Flexihtml.Searchbox":
        return self.__searchbox

    def __init__(self, title: str = "", description: str = ""):
        self.__logo_image: str = "/flexiapp/public/images/bootstrap-logo.svg"
        self.__title: str = title
        self.__description: str = description

        self.__tabs: Flexihtml.Tabs = Flexihtml.Tabs()
        self.__breadcrumb: Flexihtml.Breadcrumb = Flexihtml.Breadcrumb()
        self.__form: Flexihtml.Form = Flexihtml.Form()
        self.__table: Flexihtml.Table = Flexihtml.Table()
        self.__searchbox: Flexihtml.Searchbox = Flexihtml.Searchbox()

    def set_logo_image(self, logo_image: str):
        self.__logo_image = logo_image

    def set_title(self, title: str):
        self.__title = title

    def set_description(self, description: str):
        self.__description = description

    class Tabs:
        def __init__(self):
            self.__items: list[tuple[str, str]] = []

        def __call__(self) -> list[tuple[str, str]]:
            return self.__items

        def add(
            self,
            path: str,
            label: str,
            icon: str = '<i class="fa-solid fa-desktop"></i>',
        ):
            self.__items.append((path, label, icon))

    class Breadcrumb:
        def __init__(self):
            self.__items: list[tuple[str, str]] = []

        def __call__(self) -> list[tuple[str, str]]:
            return self.__items

        def add(self, label: str, path: str = ""):
            self.__items.append((path, label))

    class Form:
        def __init__(
            self,
            *,
            method: str = "get",
            action: str = "",
            attributes: dict[str, str] = {},
        ):
            self.__items: dict[str, dict[str, Any]] = {}
            self._attributes: dict[str, str] = attributes
            self._attributes.update({"method": method, "action": action})

        def add(self, column: InstrumentedAttribute):
            self.__items[column.key] = {"column": column}

        def content(self, name: str) -> str:
            # if isinstance(column.property, _RelationshipDeclared):
            #     html += "---"
            pass

        def __call__(self):
            html = f"<form {flatten_attributes(self._attributes)}>"

            for name, _ in self.__items.items():
                html += self.content(name)

            return html + "</form>"

    class Table:
        MAX_ITEMS_PER_PAGE: int = 15
        PAGINATION_PAGE_QNAME: str = "pg"
        PAGINATION_MAX_BUTTONS: int = 11

        @property
        def offset(self) -> int:
            return self.__offset

        @property
        def offset_limit(self) -> int:
            return self.__offset_limit

        @property
        def total_items(self) -> int:
            return self.__total_items

        def __init__(self):
            self.__items: dict[str, dict[str, Any]] = {}
            self.__labels: dict[str, dict[str, Any]] = {}
            self.__offset: int = 0
            self.__offset_limit: int = 0
            self.__total_items: int = 0
            self.__paginations: list[tuple[int, str, bool]] = []

        def __call__(
            self,
            items: list[object],
            total_items: int,
            offset: int = 0,
            item_per_page: int = MAX_ITEMS_PER_PAGE,
            nb_buttons: int = PAGINATION_MAX_BUTTONS,
        ) -> "Flexihtml.Table":
            self.__total_items = total_items
            self.__offset = offset + 1
            self.__offset_limit = offset + item_per_page
            self.__paginations = []

            if total_items == 0:
                self.__offset = 0

            if self.__offset_limit > total_items:
                self.__offset_limit = total_items

            for item in items:
                self.__items[line_uuid := str(uuid.uuid4())[0:6]] = {}

                for column_uuid, column in self.__labels.items():
                    self.__items[line_uuid][column_uuid] = {}
                    self.__items[line_uuid][column_uuid].update(column)

                    if callable(callback := column["callback"]):
                        self.__items[line_uuid][column_uuid]["callback"] = callback(item)
                    elif (method := getattr(item, callback, None)) and callable(method):
                        self.__items[line_uuid][column_uuid]["callback"] = method()
                    elif value := getattr(item, callback, None):
                        self.__items[line_uuid][column_uuid]["callback"] = value
                    else:
                        self.__items[line_uuid][column_uuid]["callback"] = str(callback)

            if total_items <= 0:
                return self

            if (current := math.ceil(offset / item_per_page) + 1) > (max_button := math.ceil(total_items / item_per_page)):
                current = max_button

            if current < 1:
                current = 1

            if nb_buttons >= max_button:
                nb_buttons = max_button

            if current <= nb_buttons / 2:
                self.__paginations = [i + 1 for i in range(0, nb_buttons)]
            elif current > max_button - (nb_buttons / 2):
                self.__paginations = [i + 1 for i in range(max_button - nb_buttons, max_button)]
            else:
                self.__paginations = [
                    i + 1
                    for i in range(
                        current - math.ceil(nb_buttons / 2),
                        current + math.floor(nb_buttons / 2),
                    )
                ]

            if not self.__paginations:
                return self

            for i, n in enumerate(self.__paginations):
                self.__paginations[i] = (n, str(n), n == current)

            if self.__paginations[0][0] > 1:
                self.__paginations.insert(0, (1, "1 ... ", False))

            if self.__paginations[-1][0] < max_button:
                self.__paginations.append((max_button, f" ... {max_button}", False))

            return self

        def items(self) -> tuple[str, dict[str, Any]]:
            return self.__items.items()

        def labels(self) -> tuple[str, dict[str, Any]]:
            return self.__labels.items()

        def paginations(self) -> list[tuple[int, str, bool]]:
            return self.__paginations

        def add(
            self,
            name: str,
            callback: Union[str, Callable[[object], str]],
            label: str = "",
            hidden: int = 0,
            sortable: int = 1,
            classname: str = "",
        ):
            self.__labels[str(uuid.uuid5(uuid.NAMESPACE_OID, name))[0:6]] = {
                "name": name,
                "callback": callback,
                "label": label if label else name.title(),
                "hidden": hidden,
                "sortable": sortable,
                "classname": classname,
            }

    class Searchbox:
        INPUT_TYPE_TEXT: str = "text"
        INPUT_TYPE_NUMBER: str = "number"
        INPUT_TYPE_DATE: str = "datetime"
        INPUT_TYPE_DATETIME: str = "datetime"
        INPUT_TYPE_TIMESTAMP: str = "timestamp"
        INPUT_TYPE_BOOLEAN: str = "boolean"
        INPUT_TYPE_ENUM: str = "enum"
        INPUT_TYPE_NULLTYPE: str = "nulltype"
        INPUT_TYPE_LIST: str = "list"
        INPUT_TYPE_GEOMETRY: str = "geometry"

        KNOWN_INPUTS: dict = {
            INPUT_TYPE_TEXT: [
                "text",
                "string",
                "autostring",
                "varchar",
                "oid",
                "inet",
                "domain",
            ],
            INPUT_TYPE_NUMBER: [
                "integer",
                "numeric",
                "smallint",
                "bigint",
                "real",
                "double_precision",
            ],
            INPUT_TYPE_BOOLEAN: ["bool", "boolean"],
            INPUT_TYPE_DATE: ["datetime", "date"],
            INPUT_TYPE_DATETIME: ["datetime", "date"],
            INPUT_TYPE_NULLTYPE: ["nulltype"],
            INPUT_TYPE_ENUM: ["enum"],
            INPUT_TYPE_LIST: ["list", "array"],
            INPUT_TYPE_GEOMETRY: ["geometry"],
            INPUT_TYPE_TIMESTAMP: ["timestamp"],
        }

        def __init__(self):
            self.__items: dict[str, dict[str, Any]] = {}

        def __call__(self, select: Select, query_params: dict) -> Select:
            for column_name, searchbox in self.items():
                sa_column = False
                sb_name = f"{column_name}_sb0"
                sb_value_1 = f"{column_name}_sb1"
                sb_value_2 = f"{column_name}_sb2"

                if searchbox["is_subquery"]:
                    for sub_select in select._raw_columns:
                        if sub_select.name == column_name:
                            sa_column = sub_select
                            break
                else:
                    sa_column = searchbox["column"]

                if sa_column is not False and (search_value_1 := query_params.get(sb_value_1, "").strip()):
                    self.__items[column_name]["input_value_1"] = search_value_1
                    self.__items[column_name]["input_value_2"] = (search_value_2 := query_params.get(sb_value_2, "").strip())
                    self.__items[column_name]["exp_selected"] = (exp := query_params.get(sb_name, "").strip())

                    if callable(callback := searchbox["callback"]):
                        select = callback(select, sa_column, exp, search_value_1, search_value_2)
                    else:
                        if exp == "is_equal":
                            select = select.where(sa_column == search_value_1)
                        elif exp == "is_not_equal":
                            select = select.where(sa_column != search_value_1)
                        elif exp == "is_less_than":
                            select = select.where(sa_column < search_value_1)
                        elif exp == "is_less_equal_than":
                            select = select.where(sa_column <= search_value_1)
                        elif exp == "is_greater_than":
                            select = select.where(sa_column > search_value_1)
                        elif exp == "is_greater_equal_than":
                            select = select.where(sa_column >= search_value_1)
                        elif exp == "is_like":
                            select = select.where(sa_column.ilike(f"%{search_value_1}%"))
                        elif exp == "is_not_like":
                            select = select.where(sa_column.not_ilike(f"%{search_value_1}%"))
                        elif exp == "is_null":
                            select = select.where(sa_column == null())
                        elif exp == "is_not_null":
                            select = select.where(sa_column != null())
                        elif exp in ["is_between", "is_not_between"] and search_value_2:
                            if exp == "is_between":
                                select = select.where(sa_column.between(search_value_1, search_value_2))
                            else:
                                select = select.where(not_(sa_column.between(search_value_1, search_value_2)))
                        elif exp in ["is_in", "is_not_in"]:
                            # TODO: not yet test
                            if exp == "is_in":
                                select = select.where(sa_column.in_(search_value_1.split(",")))
                            else:
                                select = select.where(sa_column.not_in(search_value_1.split(",")))
                        elif exp in ["is_point", "is_polygon", "is_in_radius"]:
                            continue
                        else:
                            continue

            return select

        def items(self) -> tuple[str, dict[str, Any]]:
            return self.__items.items()

        def add(
            self,
            column: Column,
            label: str,
            help_text: str = "",
            input_value_1: Union[int, str] = "",
            input_value_2: Union[int, str] = "",
            is_subquery: bool = False,
        ):
            html_input_tag = ""
            html_input_type = ""
            exp_options = {}
            value_options = {}

            for column_type, column_types in self.KNOWN_INPUTS.items():
                if column.type.__class__.__name__.lower() in column_types:
                    if column_type in [self.INPUT_TYPE_TEXT]:
                        html_input_tag = "textarea"
                        exp_options = {
                            "": "---",
                            "is_equal": "is equal",
                            "is_not_equal": "is not equal",
                            "is_like": "is like",
                            "is_not_like": "is not like",
                            "is_null": "is null",
                            "is_not_null": "is not null",
                        }
                    elif column_type in [
                        self.INPUT_TYPE_ENUM,
                        self.INPUT_TYPE_BOOLEAN,
                        self.INPUT_TYPE_NULLTYPE,
                    ]:
                        html_input_tag = "select"
                        exp_options = {
                            "": "---",
                            "is_equal": "is",
                            "is_not_equal": "is not",
                        }

                        if column_type == self.INPUT_TYPE_BOOLEAN:
                            value_options = {
                                0: "False",
                                1: "True",
                            }
                        elif column_type == self.INPUT_TYPE_NULLTYPE:
                            value_options = {"null": "NULL"}
                        else:
                            value_options = {}
                    elif column_type in [self.INPUT_TYPE_LIST]:
                        html_input_tag = "textarea"
                        exp_options = {
                            "": "---",
                            "is_in": "is in",
                            "is_not_in": "is not in",
                        }
                    elif column_type in [self.INPUT_TYPE_GEOMETRY]:
                        html_input_tag = "input"
                        html_input_type = "text"
                        exp_options = {
                            "": "---",
                            "is_point": "is point",
                            "is_polygon": "is polygon",
                            "is_in_radius": "is in radius",
                        }
                    else:
                        html_input_tag = "input"

                        if column_type in [
                            self.INPUT_TYPE_TIMESTAMP,
                            self.INPUT_TYPE_DATE,
                            self.INPUT_TYPE_DATETIME,
                        ]:
                            html_input_type = "date"
                        else:
                            html_input_type = self.INPUT_TYPE_NUMBER

                        exp_options = {
                            "": "---",
                            "is_equal": "is equal",
                            "is_not_equal": "is not equal",
                            "is_less_than": "is less than",
                            "is_less_equal_than": "is less equal than",
                            "is_greater_than": "is greater than",
                            "is_greater_equal_than": "is greater equal than",
                            "is_between": "is between .. and ..",
                            "is_not_between": "is not between .. and ..",
                            "is_null": "is null",
                            "is_not_null": "is not null",
                        }
                    break
            else:
                return

            self.__items[column.name] = {
                "column": column,
                "label": label,
                "help_text": help_text,
                "html_input_tag": html_input_tag,
                "html_input_type": html_input_type,
                "input_value_1": input_value_1,
                "input_value_2": input_value_2,
                "exp_options": exp_options,
                "exp_selected": "",
                "value_options": value_options,
                "callback": None,
                "is_subquery": is_subquery,
            }
