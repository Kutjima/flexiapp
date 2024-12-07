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


def flatten_attributes(attributes: dict) -> str:
    html = ""

    for name, value in attributes.items():
        if isinstance(value, (list, tuple, dict)):
            value = (
                json.dumps(value).replace('"', "&quot;")
                # .replace("&", "&amp;")
                # .replace("'", "&#039;")
                # .replace("<", "&lt;")
                # .replace(">", "&gt;")
            )

        html += f'{name}="{value}" '

    return html.strip()


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


class FormElement:
    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def to_string(self) -> str:
        return str(self)

    def __init__(
        self,
        name: str,
        *,
        attributes: dict[str, str] = {},
    ):
        self.attributes = {}
        self.additionals: list[FormElement] = []
        self.attributes.update(attributes)
        self.attributes["name"] = self._name = name
        self.attributes["id"] = self._id = f"flexinput-{short_uuid_text(self._name)}"

        if "class" not in self.attributes:
            self.attributes["class"] = "form-control"

    def __str__(self) -> str:
        html = ""

        for additional in self.additionals:
            html += additional._build()

        return html + self._build()

    def __add__(self, this: "FormElement"):
        if isinstance(this, FormElement):
            this.additionals.extend(self.additionals)
            this.additionals.append(self)

        return this

    def _build(self) -> str:
        raise NotImplementedError()


class _Input(FormElement):
    def __init__(
        self,
        name: str,
        value: Union[int, float, str] = "",
        *,
        type: str = "text",
        attributes: dict[str, str] = {},
    ):
        super().__init__(name, attributes=attributes)
        self.attributes["type"] = type
        self.attributes["value"] = value

    def set_value(self, value: Union[int, float, str]):
        self.attributes["value"] = value

    def _build(self) -> str:
        return f"""
            <input {flatten_attributes(self.attributes)} />
        """


class Input(_Input):
    class Date(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="date", attributes=attributes)

    class Datetime(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="datetime", attributes=attributes)

    class Time(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="time", attributes=attributes)

    class Hidden(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="hidden", attributes=attributes)

    class Password(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="password", attributes=attributes)

    class Numeric(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="number", attributes=attributes)

    class Int(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="number", attributes=attributes)

    class Float(_Input):
        def __init__(
            self,
            name: str,
            value: Union[float] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="number", attributes=attributes)

    class Text(_Input):
        @property
        def datalist_id(self) -> str:
            return self._datalist_id

        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            datalist: Union[list[str], dict[str, str]] = [],
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="text", attributes=attributes)
            self.attributes["list"] = self._datalist_id = f"datalist-{self.attributes['id']}"
            self._datalist = datalist

        def _build(self) -> str:
            html_datalist = f'<datalist id="{self._datalist_id}">'

            if isinstance(self._datalist, dict):
                for value, label in self._datalist.items():
                    html_datalist += f"<option {flatten_attributes({'value': value})}>{label} ({value})</option>"
            elif isinstance(self._datalist, list):
                for value in self._datalist:
                    html_datalist += f"<option {flatten_attributes({'value': value})} />"

            html_datalist += "</datalist>"

            return f"""
                {html_datalist}
                <input {flatten_attributes(self.attributes)} />
            """

    class File(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="file", attributes=attributes)

    class Range(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="range", attributes=attributes)
            self.attributes["class"] = "form-range"

    class Radio(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            label: str,
            checked: bool = False,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="radio", attributes=attributes)
            self.attributes["id"] = f"{self.attributes['id']}-{short_uuid_text(value)}"
            self.attributes["class"] = "form-check-input"
            self.label = label

            if checked:
                self.attributes["checked"] = 1

        def _build(self) -> str:
            return f'''
                <div class="form-check">
                    <input {flatten_attributes(self.attributes)} />
                    <label class="form-check-label" for="{self.attributes["id"]}">
                        {self.label}
                    </label>
                </div>
            '''

    class SwitchRadio(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            label: str,
            checked: bool = False,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="radio", attributes=attributes)
            self.attributes["id"] = f"{self.attributes['id']}-{short_uuid_text(value)}"
            self.attributes["class"] = "form-check-input"
            self.label = label

            if checked:
                self.attributes["checked"] = 1

        def _build(self) -> str:
            return f'''
                <div class="form-check form-switch">
                    <input {flatten_attributes(self.attributes)} />
                    <label class="form-check-label" for="{self.attributes["id"]}">
                        {self.label}
                    </label>
                </div>
            '''

    class Checkbox(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            label: str,
            checked: bool = False,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="checkbox", attributes=attributes)
            self.attributes["class"] = "form-check-input"
            self.label = label

            if checked:
                self.attributes["checked"] = 1

        def _build(self) -> str:
            return f'''
                <div class="form-check">
                    <input {flatten_attributes(self.attributes)} />
                    <label class="form-check-label" for="{self.attributes["id"]}">
                        {self.label}
                    </label>
                </div>
            '''

    class SwitchCheckbox(_Input):
        def __init__(
            self,
            name: str,
            value: Union[int, float, str] = "",
            *,
            label: str,
            checked: bool = False,
            attributes: dict[str, str] = {},
        ):
            super().__init__(name, value, type="checkbox", attributes=attributes)
            self.attributes["class"] = "form-check-input"
            self.label = label

            if checked:
                self.attributes["checked"] = 1

        def _build(self) -> str:
            return f'''
                <div class="form-check form-switch">
                    <input {flatten_attributes(self.attributes)} />
                    <label class="form-check-label" for="{self.attributes["id"]}">
                        {self.label}
                    </label>
                </div>
            '''


class Textarea(FormElement):
    def __init__(
        self,
        name: str,
        value: Union[int, float, str] = "",
        *,
        attributes: dict[str, str] = {},
    ):
        super().__init__(name, attributes=attributes)
        self.attributes["value"] = value

    def set_value(self, value: str):
        self.attributes["value"] = value

    def _build(self) -> str:
        value = ""

        if "value" in self.attributes:
            value = self.attributes.pop("value")

        return f"""
            <textarea {flatten_attributes(self.attributes)}>{value}</textarea>
        """


class Selectbox(FormElement):
    def __init__(
        self,
        name: str,
        value: Union[int, float, str] = "",
        *,
        options: dict[str, str],
        mapped_options: dict[str, str] = {},
        attributes: dict[str, str] = {},
    ):
        super().__init__(name, attributes=attributes)
        self.attributes["value"] = value
        self.attributes["class"] = "form-select"
        self.options = options
        self.mapped_options = mapped_options

    def set_value(self, value: str):
        self.attributes["value"] = value

    def _build(self) -> str:
        values = self.attributes.pop("value")

        if not isinstance(values, list):
            values = [str(values) or ""]

        html = f"""
            <select {flatten_attributes(self.attributes)}>
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
    def __init__(
        self,
        name: str,
        *,
        value: Union[int, float, str] = "",
        text_input: FormElement = Input.Text("xxxxx"),
        list_items: dict[str, str] = {},
        mapped_list_items: dict[str, str] = {},
        attributes: dict[str, str] = {},
    ):
        self._id = short_uuid_text(self._name)
        self._name = name
        self.value = value
        self.text_input = text_input
        self.list_items = list_items
        self.mapped_list_items = mapped_list_items
        self.attributes = attributes

    def _build(self) -> str:
        html = f"""
            <div id="flexilist-{self._id}" class="flexinputs flexlist">
                <div id="flexilist-input-{self._id}">{self.text_input()}</div>
                <ul id="flexilist-ul-{self._id}" class="mt-2 ps-0">
        """

        for item_value, item_label in self.list_items.items():
            tmp_attributes = {
                "class": "d-block",
                "value": item_value,
                "is-deleted": 0,
                "data-itemvalue": self.mapped_list_items.get(item_value, ""),
            }

            html += f"""
                <li {flatten_attributes(tmp_attributes)}>
                    <a href="javascript:void(0)">
                        <i class="fa-solid fa-trash"></i>
                    </a> &ndash;
                    <a href="javascript:void(0)">{item_label}</a>
                </li>
            """

        html += """
                </ul>
            <div>
        """

        return html


class Button(FormElement):
    def __init__(
        self,
        name: str,
        label: str = "Submit",
        *,
        type: str = "submit",
        value: Union[int, float, str] = "",
        attributes: dict[str, str] = {},
    ):
        super().__init__(name, attributes=attributes)
        self.attributes["class"] = "btn btn-primary"
        self.attributes["type"] = type
        self.attributes["value"] = value
        self.label = label

    def _build(self) -> str:
        return f"""
            <button {flatten_attributes(self.attributes)}>{self.label}</button>
        """


class InputGroup(FormElement):
    pass


class FormGroup:
    @property
    def id(self) -> str:
        return self._id

    @property
    def to_string(self) -> str:
        return str(self)

    def __init__(
        self,
        input: FormElement,
        *,
        label: str,
        inline: bool = False,
        colsize: int = 12,
        help_text: str = "",
        attributes: dict[str, str] = {},
    ):
        self.attributes = {}
        self.attributes.update(attributes)
        self.additionals: list[FormGroup] = []
        self.input = input
        self.label = label
        self.inline = inline
        self.colsize = colsize
        self.help_text = help_text

        if "class" not in self.attributes:
            self.attributes["class"] = "form-group flexinput-group"

        self.attributes["id"] = self._id = f"flexinput-group-{short_uuid_text(label)}"

    def __str__(self) -> str:
        html = ""

        for additional in self.additionals:
            html += additional._build()

        return html + self._build()

    def __add__(self, this: "FormGroup"):
        if isinstance(this, FormGroup):
            this.additionals.extend(self.additionals)
            this.additionals.append(self)

        return this

    def _build(self) -> str:
        if self.inline:
            return f"""
                <div class="row">
                    <label class="col-form-label col-{12 - self.colsize}">{self.label}</label>
                    <div class="col-{self.colsize}">
                        <div {flatten_attributes(self.attributes)}>
                            {self.input.to_string}
                            <small class="form-text text-muted">{self.help_text}</small>
                        </div>
                    </div>
                </div>
            """
        else:
            return f"""
                <div {flatten_attributes(self.attributes)}>
                    <label class="form-label">{self.label}</label>
                    {self.input.to_string}
                    <small class="form-text text-muted">{self.help_text}</small>
                </div>
            """


class FloatingLabel(FormGroup):
    def _build(self) -> str:
        return f"""
            <div {flatten_attributes(self.attributes)}>
                <div class="form-floating">
                    {self.input.to_string}
                    <label class="form-label" for="{self.input.id}">{self.label}</label>
                </div>
                <small class="form-text text-muted">{self.help_text}</small>
            </div>
        """

class Form:
    pass


class Table:
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
        self._build(properties)
        self.__properties__ = properties
        self.__total_items_count__: int = -1

    def __getitem__(self, key):
        if key is Ellipsis:
            return "Accessing all elements"
        else:
            return f"Accessing element {key}"

    def _build(self, properties: dict) -> "T":
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

        def _build(self, name: str) -> str:
            # if isinstance(column.property, _RelationshipDeclared):
            #     html += "---"
            pass

        def __call__(self):
            html = f"<form {flatten_attributes(self.__attributes)}>"

            for name, _ in self.__items.items():
                html += self._build(name)

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
