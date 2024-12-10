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

    return to_encode


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
        self._attributes: dict[str, str] = {}
        self._attributes.update(attributes)
        self._previous_items: list[XHtmlElement] = []

    def __add__(self, this: "XHtmlElement") -> "XHtmlElement":
        if isinstance(this, XHtmlElement):
            this._previous_items.extend(self._previous_items)
            this._previous_items.append(self)

        return this

    def __getitem__(self, key: str) -> Any | None:
        if key is Ellipsis:
            return self._attributes

        return self._attributes.get(key)

    def __setitem__(self, key: str, value: int | float | str):
        if key is Ellipsis and isinstance(value, dict):
            self._attributes.update(value)
        elif key is not Ellipsis:
            self._attributes[key] = value

    def template(self) -> str:
        return ""

    def previous_template(self) -> str:
        html = ""

        for item in self._previous_items:
            html += item.template()

        return html

    def content(self) -> str:
        return self.previous_template() + self.template()


class HtmlElement(XHtmlElement):
    def __init__(self, content: str | XHtmlElement, *, tag: str = "div", attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self._tag = tag
        self._content = content

    def template(self) -> str:
        tag = self._tag.lower()
        content = self._content

        if isinstance(self._content, XHtmlElement):
            content = self._content.template()

        return f"<{tag} {flatten_attributes(self._attributes)}>{content}</{tag}>"


class FormElement(XHtmlElement):
    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def value(self) -> int | float | str:
        return self._attributes["value"]

    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self._attributes["id"] = self._id = f"flexinput-{short_uuid_text(name)}"
        self._attributes["name"] = self._name = name
        self._attributes["value"] = value


class Input(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, type: str = "text", attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self._attributes["type"] = type
        self._attributes["class"] = "form-control"

    def template(self) -> str:
        return f"""
            <input {flatten_attributes(self._attributes)} />
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
        self._attributes["step"] = step


class Float(Input):
    def __init__(self, name: str, value: Union[float] = "", *, step: int | float = 0.01, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="number", attributes=attributes)
        self._attributes["step"] = step


class Text(Input):
    @property
    def datalist_id(self) -> str:
        return self._datalist_id

    def __init__(self, name: str, value: int | float | str = "", *, datalist: list[str] | dict[str, str] = [], attributes: dict[str, str] = {}):
        super().__init__(name, value, type="text", attributes=attributes)
        self._datalist = datalist
        self._attributes["list"] = self._datalist_id = f"datalist-{self._attributes['id']}"

    def template(self) -> str:
        html_datalist = f'<datalist id="{self._datalist_id}">'

        if isinstance(self._datalist, dict):
            for value, label in self._datalist.items():
                html_datalist += f"<option {flatten_attributes({'value': value})}>{label}</option>"
        elif isinstance(self._datalist, list):
            for value in self._datalist:
                html_datalist += f"<option {flatten_attributes({'value': value})} />"

        html_datalist += "</datalist>"

        return f"""
            {html_datalist}
            <input {flatten_attributes(self._attributes)} />
        """


class Textauto(Text):
    pass


class File(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="file", attributes=attributes)


class Photo(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="file", attributes=attributes)
        self.app_id = f"app_{short_uuid_text(self._id)}"
        self._attributes["multiple"] = ""
        self._attributes["accept"] = "image/*"

    def template(self) -> str:
        self._attributes["onchange"] = f"{self.app_id}.event_onchange(this);"
        html = f"""
            <script>
                const {self.app_id} = {{
                    event_onchange: function(input) {{
                        const [file] = input.files;
                        const $showcase = $("img#showcase-{self._id}");

                        if (file) {{
                            $showcase.attr("src", window.URL.createObjectURL(file));
                            $showcase.on("onload", function() {{
                                window.URL.revokeObjectURL($showcase.attr("src"));
                            }});

                            return true;
                        }}

                        return $showcase.attr("src", "#[NO FILE SELECTED]");
                    }},
                }};
            </script>
            <div class="mb-2">
                <img id="showcase-{self._id}" src="#[NO FILE SELECTED]" class="img-fluid border border-2 p-1" style="min-width: 312px; min-height: 162px;" />
            </div>
        """

        return html + super().template()


class Video(Input):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="file", attributes=attributes)
        self.app_id = f"app_{short_uuid_text(self._id)}"
        self._attributes["multiple"] = ""
        self._attributes["accept"] = "video/*"

    def template(self) -> str:
        self._attributes["onchange"] = f"{self.app_id}.event_onchange(this);"
        html = f"""
            <script>
                const {self.app_id} = {{
                    event_onchange: function(input) {{
                        const [file] = input.files;
                        const $showcase = $("video#showcase-{self._id}");

                        if (file) {{
                            $showcase.attr("src", window.URL.createObjectURL(file));
                            $showcase.on("onload", function() {{
                                window.URL.revokeObjectURL($showcase.attr("src"));
                            }});

                            return true;
                        }}

                        return $showcase.attr("src", "#[NO FILE SELECTED]");
                    }},
                }};
            </script>
            <div class="mb-2">
                <video id="showcase-{self._id}" src="#[NO FILE SELECTED]" class="img-fluid border border-2 p-1" controls="controls">
                    Your browser does not support the video tag.
                </video>
            </div>
        """

        return html + super().template()


class Range(Input):
    def __init__(self, name: str, value: int | float | str = "", *, min_value: int | float = 0, max_value: int | float = 100, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="range", attributes=attributes)
        self._attributes["min"] = min_value
        self._attributes["max"] = max_value
        self._attributes["class"] = "form-range"


class Radio(Input):
    def __init__(self, name: str, value: int | float | str = "", *, label: str, checked: bool = False, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="radio", attributes=attributes)
        self.label = label
        self._attributes["id"] = f"{self._attributes['id']}-{short_uuid_text(value)}"
        self._attributes["class"] = "form-check-input"

        if checked:
            self._attributes["checked"] = 1

    def template(self) -> str:
        return f'''
            <div class="form-check">
                <input {flatten_attributes(self._attributes)} />
                <label class="form-check-label" for="{self._attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class SwitchRadio(Radio):
    def template(self) -> str:
        return f'''
            <div class="form-check form-switch">
                <input {flatten_attributes(self._attributes)} />
                <label class="form-check-label" for="{self._attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class Checkbox(Input):
    def __init__(self, name: str, value: int | float | str = "", *, label: str, checked: bool = False, attributes: dict[str, str] = {}):
        super().__init__(name, value, type="checkbox", attributes=attributes)
        self.label = label
        self._attributes["class"] = "form-check-input"

        if checked:
            self._attributes["checked"] = 1

    def template(self) -> str:
        return f'''
            <div class="form-check">
                <input {flatten_attributes(self._attributes)} />
                <label class="form-check-label" for="{self._attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class SwitchCheckbox(Checkbox):
    def template(self) -> str:
        return f'''
            <div class="form-check form-switch">
                <input {flatten_attributes(self._attributes)} />
                <label class="form-check-label" for="{self._attributes["id"]}">
                    {html_encode(self.label)}
                </label>
            </div>
        '''


class Button(Input):
    def __init__(self, name: str, label: str = "Submit", *, type: str = "submit", value: int | float | str = "", attributes: dict[str, str] = {}):
        super().__init__(name, value, type=type, attributes=attributes)
        self.label = label
        self._attributes["class"] = "btn btn-primary"

    def template(self) -> str:
        return f"""
            <button {flatten_attributes(self._attributes)}>{self.label}</button>
        """


class Textarea(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self._attributes["class"] = "form-control"

    def template(self) -> str:
        value = ""

        if "value" in self._attributes:
            value = self._attributes.pop("value")

        return f"""
            <textarea {flatten_attributes(self._attributes)}>{value}</textarea>
        """


class Selectbox(FormElement):
    def __init__(self, name: str, value: int | float | str = "", *, options: dict[str, str], mapped_options: dict[str, str] = {}, attributes: dict[str, str] = {}):
        super().__init__(name, value, attributes=attributes)
        self.options = options
        self.mapped_options = mapped_options
        self._attributes["class"] = "form-select"

    def template(self) -> str:
        values = []

        if "value" in self._attributes:
            values = self._attributes.pop("value")

        if not isinstance(values, list):
            values = [str(values) or ""]

        html = f"""
            <select {flatten_attributes(self._attributes)}>
        """

        for item_value, item_label in self.options.items():
            tmp_attributes = {
                "value": item_value,
                "data-optionvalue": self.mapped_options.get(item_value, ""),
            }

            if item_value in values:
                tmp_attributes["selected"] = 1

            html += f"""
                <option {flatten_attributes(tmp_attributes)}>{item_label}</option>
            """

        html += """
            </select>
        """

        return html


class Listbox(FormElement):
    def __init__(self, name: str, *, input: FormElement, list_items: list[str] = [], attributes: dict[str, str] = {}):
        if not isinstance(input, (Int, Float, Text, Textauto, Textarea, Selectbox)):
            raise ValueError(f"Param 'input' must be Int, Float, Text, Textauto, Textarea or Selectbox. Got: {type(input)}.")

        super().__init__(name, attributes=attributes)
        self.app_id = f"app_{short_uuid_text(self._id)}"
        self.input = input
        self.list_items = list_items

    def item_template(self, content: str, classname: str = "") -> str:
        return f"""
            <li class="d-block flexilist-ul-item">
                &rarrhk; <a 
                    href="javascript:void(0)"
                    class="flexilist-ul-item-edit {classname}"
                    onclick="{self.app_id}.update_item(this);">{content}</a>
                <a 
                    href="javascript:void(0)"
                    class="flexilist-ul-item-action"
                    is-deleted="0"
                    onclick="{self.app_id}.delete_item(this);">&ndash; <i class="fa-solid fa-trash"></i></a>
            </li>
        """

    def template(self) -> str:
        self.input["onblur"] = f"{self.app_id}.event_onblur(this);"
        self.input["oninput"] = f"{self.app_id}.event_oninput(this);"
        html = f"""
            <div id="flexilist-{self._id}" class="flexinputs flexlist">
                <div id="flexilist-input-{self._id}">
                    {self.input.content()}
                </div>
                <div class="float-end">
                    <a 
                        href="javascript:void(0)"
                        class="mt-2"
                        onclick="{self.app_id}.add_item(this);">add</a>
                </div>
                <div class="clearfix"></div>
                <ul 
                    name="{self._name}"
                    id="flexilist-ul-{self._id}"
                    class="flexilist-ul mt-2 ps-0">
        """

        for item in self.list_items:
            html += self.item_template(html_encode(item))

        html += f"""
                </ul>
            </div>
            <script>
                const {self.app_id} = {{
                    item_template: function(content, classname) {{
                        return `{self.item_template("${this.html_encode(content)}", "${classname || ''}").strip()}`;
                    }},
                    add_item: function(button) {{
                        const content = ($("#flexilist-input-{self._id}").find("#{self.input.id}").val() || "").trim();
                        const $is_connected = $("ul#flexilist-ul-{self._id} a.flexilist-ul-item-edit.is-connected");

                        if (content != "" && $is_connected.length == 0) {{
                            $("ul#flexilist-ul-{self._id}").append(this.item_template(content));
                            $("#flexilist-input-{self._id}").find("#{self.input.id}").val("");
                        }} else if (content == "") {{
                            $("#flexilist-input-{self._id}").find("#{self.input.id}").focus();
                            $("ul#flexilist-ul-{self._id}").append(this.item_template("", "is-connected"));
                        }}
                    }},
                    update_item: function(item) {{
                        const $item = $(item);

                        if (!$item.parent("li").hasClass("is-deleted")) {{
                            $("ul#flexilist-ul-{self._id} a.flexilist-ul-item-edit").removeClass("is-connected"); 
                            $item.addClass("is-connected");
                            $("#flexilist-input-{self._id}").find("#{self.input.id}").val($item.text()).focus();
                        }}
                    }},
                    delete_item: function(button) {{
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
                    }},
                    event_oninput: function(input) {{
                        const $input = $(input);
                        const $is_connected = $("ul#flexilist-ul-{self._id} a.flexilist-ul-item-edit.is-connected");

                        if ($is_connected.length > 0)
                            $is_connected.text($input.val());
                    }},
                    event_onblur: function(input) {{
                        const $input = $(input);
                        const $is_connected = $("ul#flexilist-ul-{self._id} a.flexilist-ul-item-edit.is-connected");

                        if ($is_connected.length > 0) {{
                            $is_connected.removeClass("is-connected");
                            $input.val("");
                        }}
                        
                        this.clean_items();
                    }},
                    clean_items: function() {{
                        $("ul#flexilist-ul-{self._id} a.flexilist-ul-item-edit").each(function(i, e) {{
                            const $item = $(e);

                            if ($item.is(":empty"))
                                $item.parent("li").remove();
                        }})
                    }},
                    html_encode: function(unsafe) {{
                        return unsafe
                            .replace(/&/g, "&amp;")
                            .replace(/</g, "&lt;")
                            .replace(/>/g, "&gt;")
                            .replace(/"/g, "&quot;")
                            .replace(/'/g, "&#039;");
                    }},
                }};
            </script>
        """

        return html


class Dictbox(FormElement):
    def __init__(self, name: str, *, inputs: dict[str, FormElement], list_items: list[dict[str, str]] = [], attributes: dict[str, str] = {}):
        for i, input in inputs.items():
            if not isinstance(input, (Int, Float, Text, Textauto, Textarea, Selectbox)):
                raise ValueError(f"Param 'input' must be Int, Float, Text, Textauto, Textarea or Selectbox. Got: {type(input)} (param: {i}).")

        super().__init__(name, attributes=attributes)
        self.app_id = f"app_{short_uuid_text(self._id)}"
        self.inputs = inputs
        self.list_items = list_items

    def item_template(self, item: dict, classname: str = "") -> str:
        content =""

        for label, input in self.inputs.items():
            content += f"""
                <li class="mb-0 pb-0 d-block">
                    <a
                        name="{input.name}"
                        href="javascript:void(0)"
                        onclick="{self.app_id}.update_item(this);">
                            <b>{label}</b>: 
                            <span>{html_encode(str(item.get(input.name, "")))}</span>
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
                    onclick="{self.app_id}.delete_item(this);">&ndash; <i class="fa-solid fa-trash"></i></a>
            </li>
        """
    
    def template(self) -> str:
        content = ""

        for label, input in self.inputs.items():
            input["onblur"] = f"{self.app_id}.event_onblur(this);"
            input["oninput"] = f"{self.app_id}.event_oninput(this);"
            content += (FormGroup(input, label=label, colsize=9)).content()

        html = f"""
            <div id="flexilist-{self._id}" class="flexinputs flexlist">
                <div id="flexilist-input-{self._id}">
                    {content}
                </div>
                <div class="float-end">
                    <a 
                        href="javascript:void(0)"
                        class="mt-2"
                        onclick="{self.app_id}.add_item(this);">add</a>
                </div>
                <div class="clearfix"></div>
                <ul 
                    name="{self._name}"
                    id="flexilist-ul-{self._id}"
                    class="flexilist-ul tallest mt-2 ps-0">
        """

        for item in self.list_items:
            html += self.item_template(item)

        html += f"""
                </ul>
            </div>
            <script>
                const {self.app_id} = {{
                    item_template: function(classname) {{
                        return `{self.item_template({}, "${classname || ''}").strip()}`;
                    }},
                    add_item: function(button) {{
                        const $button = $(button);
                        const $is_connected = $("ul#flexilist-ul-{self._id} .flexilist-ul-item-edit.is-connected");

                        if ($is_connected.length > 0) {{
                        
                        }} else {{
                            const $item = $(this.item_template("is-connected"));

                            $item.find(".flexilist-ul-item-edit a").each(function(i, e) {{
                                const $a = $(e);
                                const $input = $("#flexilist-input-{self._id}").find("[name=" + $a.attr("name") + "]");
                                
                                $a.find("span").text($input.val());
                            }});
                            $("ul#flexilist-ul-{self._id}").append($item);
                            $("#flexilist-input-{self._id}").find("input, textarea, select").each(function(i, e) {{
                                if (i == 0) {{
                                    $(e).focus();
                                }}
                            }});
                        }}
                    }},
                    update_item: function(item) {{
                        const $item = $(item);
                        const $item_dict = $item.parents("div.flexilist-ul-item-edit:first");

                        if (!$item_dict.parent("li.flexilist-ul-item").hasClass("is-deleted")) {{
                            $("ul#flexilist-ul-{self._id} .flexilist-ul-item-edit").removeClass("is-connected"); 
                            $item_dict.addClass("is-connected");
                            $item_dict.find("li a").each(function(i, e) {{
                                const $a = $(e);
                                const $input = $("#flexilist-input-{self._id}").find("[name=" + $a.attr("name") + "]");

                                if ($item.attr("name") == $a.attr("name"))
                                    $input.focus();

                                $input.val($a.find("span").text());
                            }});
                        }}
                    }},
                    delete_item: function(button) {{
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
                    }},
                    event_oninput: function(input) {{
                        const $input = $(input);

                        $("ul#flexilist-ul-{self._id} .flexilist-ul-item-edit.is-connected a").each(function(i, e) {{
                            const $a = $(e);

                            if ($a.attr("name") == $input.attr("name"))
                                $a.find("span").text($input.val());
                        }});
                    }},
                    event_onblur: function(input) {{
                        const $input = $(input);
                        const $is_connected = $("ul#flexilist-ul-{self._id} .flexilist-ul-item-edit.is-connected");

                        if ($is_connected.length > 0) {{
                            var is_still_focused = false;

                            setTimeout(function() {{
                                $("#flexilist-input-{self._id}").find("input, textarea, select").each(function(i, e) {{
                                    if (is_still_focused == false && $(e).is(":focus")) {{
                                        is_still_focused = true;
                                    }}
                                }});

                                if (is_still_focused == false) {{
                                    $is_connected.removeClass("is-connected");

                                    $("#flexilist-input-{self._id}").find("input, textarea, select").each(function(i, e) {{
                                        $(e).val("");
                                    }});
                                }}
                            }}, 100);
                        }}
                        
                        this.clean_items();
                    }},
                    clean_items: function() {{
                    
                    }},
                }};
            </script>
        """

        return html


class Mediabox(Listbox):
    pass


class FormGroup(XHtmlElement):
    @property
    def id(self) -> str:
        return self._id

    def __init__(self, input: FormElement, *, label: str, colsize: int = 12, help_text: str = "", attributes: dict[str, str] = {}):
        super().__init__(attributes)
        self.input = input
        self.label = label
        self.colsize = colsize
        self.help_text = help_text
        self._attributes["id"] = self._id = f"flexinput-group-{short_uuid_text(label)}"
        self._attributes["class"] = "form-group flexinput-group"

    def template(self) -> str:
        if isinstance(self.input, Hidden):
            return self.input.content()

        if self.colsize < 12:
            return f"""
                <div {flatten_attributes(self._attributes)}>
                    <div class="row">
                        <label class="col-form-label col-{12 - self.colsize}">{html_encode(self.label)}</label>
                        <div class="col-{self.colsize}">
                            {self.input.content()}
                            <small class="form-text text-muted">{html_encode(self.help_text)}</small>
                        </div>
                    </div>
                </div>
            """
        else:
            return f"""
                <div {flatten_attributes(self._attributes)}>
                    <label class="form-label">{html_encode(self.label)}</label>
                    {self.input.content()}
                    <small class="form-text text-muted">{html_encode(self.help_text)}</small>
                </div>
            """


class FloatingLabel(FormGroup):
    def template(self) -> str:
        return f"""
            <div {flatten_attributes(self._attributes)}>
                <div class="form-floating">
                    {self.input.content()}
                    <label class="form-label" for="{self.input.id}">{html_encode(self.label)}</label>
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
        Photo: FormElement = Photo
        Video: FormElement = Video
        Range: FormElement = Range
        Radio: FormElement = Radio
        SwitchRadio: FormElement = SwitchRadio
        Checkbox: FormElement = Checkbox
        SwitchCheckbox: FormElement = SwitchCheckbox
        Button: FormElement = Button
        Text: FormElement = Text
        Textauto: FormElement = Textauto
        Textarea: FormElement = Textarea
        Selectbox: FormElement = Selectbox
        Listbox: FormElement = Listbox
        Dictbox: FormElement = Dictbox
        Mediabox: FormElement = Mediabox
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
            self.__attributes: dict[str, str] = attributes
            self.__attributes.update({"method": method, "action": action})

        def add(self, column: InstrumentedAttribute):
            self.__items[column.key] = {"column": column}

        def content(self, name: str) -> str:
            # if isinstance(column.property, _RelationshipDeclared):
            #     html += "---"
            pass

        def __call__(self):
            html = f"<form {flatten_attributes(self.__attributes)}>"

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
