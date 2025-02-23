from pathlib import Path
from fastapi import APIRouter, Response
from fastapi.openapi.docs import get_swagger_ui_html

router = APIRouter()

PATH_APP_PY = Path(__file__)
PATH_PROJECT = PATH_APP_PY.parent


@router.get('/docs')
def swagger_docs():
    rsp = get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Pink Page API Server Swagger",
        swagger_css_url="/swagger/swagger_css",
        swagger_js_url="/swagger/swagger_js"
    )
    return rsp


@router.get('/swagger_css')
def swagger_css():
    with open(Path(PATH_PROJECT, "static/swagger-ui.css"), 'rt', encoding='utf-8') as f:
        css = f.read()
    return Response(css, headers={"Content-type": "text/css"})


@router.get('/swagger_js')
def swagger_js():
    with open(Path(PATH_PROJECT, "static/swagger-ui.js"), 'rt', encoding='utf-8') as f:
        js = f.read()
    return Response(js, headers={"Content-type": "text/javascript"})
