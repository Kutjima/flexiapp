import os
import sys
import time
import pathlib
import requests

sys.path.append("../module/")

import sqlalchemy as sqlal

from fastapi import status, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from flexiapp import (
    FLEXIAPP_PATH,
    HtmlElement,
    Form,
    Flexihtml,
    Fleximodel,
    PhotoFrame,
)

APPLICATION_PATH = pathlib.Path(__file__).resolve().parent

# FastAPI
app = FastAPI(title="Flexiapp")
# app.mount("/public", StaticFiles(directory="public/"), name="public")
app.mount("/flexiapp/public", StaticFiles(directory=f"{FLEXIAPP_PATH}/public/"), name="flexapp/public")

# Jinja2 Env
env = Environment(
    loader=FileSystemLoader([
        "app/templates/",
        f"{FLEXIAPP_PATH}/app/templates/",
    ])
)

# Flexihtml
flexihtml = Flexihtml("Hello World !")
# flexihtml.set_logo_image("/public/images/logos/logo-h.png")
flexihtml.tabs.add("../", "Dashboard", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../text-input", "Text Input", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../file", "File", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../radio", "Radio", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../checkbox", "Checkbox", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../selectbox", "Select Box", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../searchbox", "Search Box", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../listbox", "List Box", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../dictbox", "Dict Box", '<i class="fa-solid fa-desktop"></i>')
flexihtml.tabs.add("../floating-label", "Floating Label", '<i class="fa-solid fa-desktop"></i>')

COLSIZE = 8

@app.get("/")
def home(request: Request):
    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": "",
        }),
    )

@app.get("/text-input")
def text_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Hidden(
            "Hidden",
            "Hidden",
        ),
        label="Hidden",
        help_text="Hidden",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Password(
            "Password",
            "Password",
        ),
        label="Password",
        help_text="Password",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Int(
            "Int",
            123,
        ),
        label="Int",
        help_text="Int",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Float(
            "Float",
            123.456,
        ),
        label="Float",
        help_text="Float",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Text(
            "NormalText",
            "Text",
        ),
        label="Text",
        help_text="Text",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Text(
            "Text with datalist",
            "USA",
            data=[
                "France",
                "USA",
                "Mauritius",
            ],
        ),
        label="Text with datalist",
        help_text="Text",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Text(
            "",
            "",
            data="/an-endpoint-2",
        ),
        label="Text with datalist (endpoint)",
        help_text="Text with datalist (endpoint)",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        PhotoFrame(
            Form.e.Text(
                "TextPreview",
                "/public/images/logos/logo-h.png",
            ),
            width="100px",
        ),
        label="Text Preview",
        help_text="Text Preview",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Textarea(
            "Textarea",
            "Textarea",
        ),
        label="Textarea",
        help_text="Textarea",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Date(
            "Date",
            "",
        ),
        label="Date",
        help_text="Date",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.DateRange(
            "DateRange",
            "",
            second_name="world"
        ),
        label="Date Range",
        help_text="Date Range",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Datetime(
            "Datetime",
            "",
        ),
        label="Datetime",
        help_text="Datetime",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Time(
            "Time",
            "",
        ),
        label="Time",
        help_text="Time",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.TimeRange(
            "TimeRange",
            "",
        ),
        label="Time Range",
        help_text="Time Range",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Range("Range", 10),
        label="Range",
        help_text="Range",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/file")
def file_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.File("File"),
        label="File",
        help_text="File",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )


@app.get("/selectbox")
def selectbox_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Selectbox(
            "Selectbox",
            "us",
            options={
                "fr": "France",
                "us": "USA",
                "mu": "Mauritius",
            },
        ),
        label="Selectbox",
        help_text="Selectbox",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        PhotoFrame(
            Form.e.Selectbox(
                "TextPreview2",
                "https://cdn-0.generatormix.com/images/pokemon/pikachu.jpg",
                options={
                    x: os.path.basename(x)
                    for x in [
                        "https://cdn-0.generatormix.com/images/pokemon/pikachu.jpg",
                        "https://cdn-0.generatormix.com/images/pokemon/unfezant.jpg",
                        "https://cdn-0.generatormix.com/images/pokemon/lampent.jpg",
                        "https://cdn-0.generatormix.com/images/pokemon/inkay.jpg",
                    ]
                },
            ),
            width="100px",
        ),
        label="Text Preview",
        help_text="Text Preview",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/radio")
def radio_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Radio(
            "Radio",
            "Radio01",
            label="Radio 01",
        )
        + Form.e.Radio(
            "Radio",
            "Radio02",
            label="Radio 02",
            checked=True,
        )
        + Form.e.Radio(
            "Radio",
            "Radio03",
            label="Radio 03",
        ),
        label="Radios",
        help_text="Radios",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.SwitchRadio(
            "SwitchRadio",
            "SwitchRadio01",
            label="SwitchRadio 01",
        )
        + Form.e.SwitchRadio(
            "SwitchRadio",
            "SwitchRadio02",
            label="SwitchRadio 02",
        )
        + Form.e.SwitchRadio(
            "SwitchRadio",
            "SwitchRadio03",
            label="SwitchRadio 03",
            checked=True,
        ),
        label="SwitchRadios",
        help_text="SwitchRadios",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/checkbox")
def checkbox_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Checkbox(
            "Checkbox",
            "Checkbox",
            label="Checkbox",
        ),
        label="Checkbox",
        help_text="Checkbox",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Checkbox(
            "Checkbox01",
            "Checkbox01",
            label="Checkbox 01",
        )
        + Form.e.Checkbox(
            "Checkbox02",
            "Checkbox02",
            label="Checkbox 02",
            checked=True,
        ),
        label="Checkboxes",
        help_text="Checkboxes",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.SwitchCheckbox(
            "SwitchCheckbox01",
            "SwitchCheckbox01",
            label="SwitchCheckbox 01",
        )
        + Form.e.SwitchCheckbox(
            "SwitchCheckbox02",
            "SwitchCheckbox02",
            label="SwitchCheckbox 02",
        )
        + Form.e.SwitchCheckbox(
            "SwitchCheckbox03",
            "SwitchCheckbox03",
            label="SwitchCheckbox 03",
            checked=True,
        ),
        label="SwitchCheckboxes",
        help_text="SwitchCheckboxes",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/searchbox")
def searchbox_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Searchbox(
            "Searchbox",
            endpoint="/an-endpoint",
        ),
        label="Searchbox",
        help_text="Searchbox",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/listbox")
def listbox_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Listbox(
            "ListboxInput",
            element=Form.e.Text("XXXX"),
            list_items=["France", "Mauritius"],
        ),
        label="Listbox Input",
        help_text="Listbox Input",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Listbox(
            "ListboxTextarea",
            element=Form.e.Textarea("YYYYY"),
            list_items=[
                '<a href="ffF">sssdfdf</a>',
                "HTML Arrows is a comprehensive reference website for finding HTML symbol codes and entities, \
                    ASCII characters and Unicode hexadecimal values to use in your web design. Browse in grid or table format, search for HTML symbol",
            ],
        ),
        label="Listbox Textarea",
        help_text="Listbox Textarea",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Listbox(
            "ListboxSelectbox",
            element=Form.e.Selectbox(
                "ZZZZZ",
                "us",
                options={
                    "": "",
                    "France": "France",
                    "USA": "USA",
                    "Mauritius": "Mauritius",
                },
            ),
            list_items=["Mauritius"],
        ),
        label="Listbox Selectbox",
        help_text="Listbox Selectbox",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Listbox(
            "ListboxSearchbox",
            element=Form.e.Searchbox(
                "ListboxSearchbox",
                endpoint="/an-endpoint",
            ),
            list_items=["Mauritius"],
        ),
        label="Listbox Searchbox",
        help_text="Listbox Searchbox",
        colsize=COLSIZE,
    )
    html += Form.e.FormGroup(
        Form.e.Listbox(
            "TextPreview3",
            element=PhotoFrame(
                Form.e.Selectbox(
                    "TextPreview3",
                    "https://cdn-0.generatormix.com/images/pokemon/lampent.jpg",
                    options={
                        x: os.path.basename(x)
                        for x in [
                            "https://cdn-0.generatormix.com/images/pokemon/pikachu.jpg",
                            "https://cdn-0.generatormix.com/images/pokemon/unfezant.jpg",
                            "https://cdn-0.generatormix.com/images/pokemon/lampent.jpg",
                            "https://cdn-0.generatormix.com/images/pokemon/inkay.jpg",
                        ]
                    },
                ),
            ),
            list_items=["https://cdn-0.generatormix.com/images/pokemon/pikachu.jpg"],
        ),
        label="Text Preview 3",
        help_text="Text Preview 3",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/dictbox")
def dictbox_example(request: Request):
    html = Form.e.FormGroup(
        Form.e.Dictbox(
            "Dictbox",
            elements={
                "ID": Form.e.Int("id"),
                "Fullname": Form.e.Text("fullname"),
                "Sex": Form.e.Selectbox(
                    "gender",
                    "m",
                    options={
                        "": "",
                        "m": "Male",
                        "f": "Female",
                    },
                ),
                "Small description": Form.e.Textarea("description", ""),
            },
            list_items=[
                {
                    "id": 100001,
                    "fullname": "John Doe",
                    "gender": "m",
                    "description": "HTML Arrows is a comprehensive reference website for finding HTML symbol codes and entitie",
                },
                {
                    "id": 100002,
                    "fullname": "Jane Doe",
                    "gender": "f",
                },
            ],
        ),
        label="Listbox Dictbox",
        help_text="Listbox Dictbox",
        colsize=COLSIZE,
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )

@app.get("/floating-label")
def floating_label_example(request: Request):
    html = Form.e.FloatingLabel(
        Form.e.Text(
            "FloatingLabelText",
            "FloatingLabel Text",
        ),
        label="FloatingLabel Text",
        help_text="FloatingLabel Text",
    )
    html += Form.e.FloatingLabel(
        Form.e.Textarea(
            "FloatingLabelTextarea",
            "FloatingLabel Textarea",
        ),
        label="FloatingLabel Textarea",
        help_text="FloatingLabel Textarea",
    )
    html += Form.e.FloatingLabel(
        Form.e.Selectbox(
            "FloatingLabelSelectbox",
            "us",
            options={
                "": "---",
                "fr": "France",
                "us": "USA",
                "mu": "Mauritius",
            },
        ),
        label="FloatingLabel Selectbox",
        help_text="FloatingLabel Selectbox",
    )
    html += Form.e.FormGroup(
        Form.e.Button(
            "Cancel",
            label="Cancel",
            type="reset",
        )
        + Form.e.Button(
            "Submit",
            label="Send data",
        ),
        label="",
    )

    return HTMLResponse(
        status_code=status.HTTP_200_OK,
        content=env.get_template("backoffice/form.html").render({
            "timestamp": time.time(),
            "flexihtml": flexihtml,
            "html": html.content(),
        }),
    )