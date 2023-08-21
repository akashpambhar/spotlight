"""
table api endpoints
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse, Response
from pydantic import BaseModel

from renumics.spotlight.backend.exceptions import FilebrowsingNotAllowed, InvalidPath
from renumics.spotlight.app import SpotlightApp
from renumics.spotlight.app_config import AppConfig
from renumics.spotlight.dtypes.typing import get_column_type_name
from renumics.spotlight.io.path import is_path_relative_to
from renumics.spotlight.reporting import emit_timed_event

from renumics.spotlight.dtypes import (
    Audio,
    Category,
    Embedding,
    Image,
    Mesh,
    Sequence1D,
    Video,
)


# for now specify all lazy dtypes right here
# we should probably move closer to the actual dtype definition for easier extensibility
LAZY_DTYPES = [Embedding, Mesh, Image, Video, Sequence1D, np.ndarray, Audio, str]


class Column(BaseModel):
    """
    a single table column
    """

    name: str
    editable: bool
    optional: bool
    role: str
    values: List[Any]
    description: Optional[str]
    tags: Optional[List[str]]
    categories: Optional[Dict[str, int]]


class Table(BaseModel):
    """
    a table slice
    """

    uid: str
    filename: str
    columns: List[Column]
    generation_id: int


router = APIRouter()


@router.get(
    "/",
    response_model=Table,
    response_class=ORJSONResponse,
    tags=["table"],
    operation_id="get_table",
)
@emit_timed_event
def get_table(request: Request) -> ORJSONResponse:
    """
    table slice api endpoint
    """
    app: SpotlightApp = request.app
    data_store = app.data_store
    if data_store is None:
        return ORJSONResponse(
            Table(
                uid="",
                filename="",
                columns=[],
                generation_id=-1,
            ).dict()
        )

    columns = []
    for column_name in data_store.column_names:
        dtype = data_store.dtypes[column_name]
        values = data_store.get_converted_values(column_name, simple=True)
        meta = data_store.get_column_metadata(column_name)
        if dtype == Category:
            categories = data_store._data_source.get_column_categories(column_name)
        else:
            categories = {}
        column = Column(
            name=column_name,
            values=values,
            editable=meta.editable,
            optional=meta.nullable,
            role=get_column_type_name(dtype),
            categories=categories,
            description=meta.description,
            tags=meta.tags,
        )
        columns.append(column)

    return ORJSONResponse(
        Table(
            uid=data_store.uid,
            filename=data_store.name,
            columns=columns,
            generation_id=data_store.generation_id,
        ).dict()
    )


@router.get(
    "/{column}/{row}",
    tags=["table"],
    operation_id="get_cell",
)
async def get_table_cell(
    column: str, row: int, generation_id: int, request: Request
) -> Response:
    """
    table cell api endpoint
    """
    app: SpotlightApp = request.app
    data_store = app.data_store
    if data_store is None:
        return ORJSONResponse(None)
    data_store.check_generation_id(generation_id)

    value = data_store.get_converted_value(column, row, simple=False)

    if isinstance(value, bytes):
        return Response(value, media_type="application/octet-stream")

    return ORJSONResponse(value)


@router.get(
    "/{column}/{row}/waveform",
    response_model=Optional[List[float]],
    tags=["table"],
    operation_id="get_waveform",
)
async def get_waveform(
    column: str, row: int, generation_id: int, request: Request
) -> ORJSONResponse:
    """
    table cell api endpoint
    """
    app: SpotlightApp = request.app
    data_store = app.data_store
    if data_store is None:
        return ORJSONResponse(None)
    data_store.check_generation_id(generation_id)

    waveform = data_store.get_waveform(column, row)

    return ORJSONResponse(waveform)


class AddColumnRequest(BaseModel):
    """
    Add Column request model
    """

    dtype: str


@router.post("/open/{path:path}", tags=["table"], operation_id="open")
async def open_table(path: str, request: Request) -> None:
    """
    Open the specified table file

    :raises InvalidPath: if the supplied path is outside the project root
                         or points to an incompatible file
    """
    app: SpotlightApp = request.app

    if not app.filebrowsing_allowed:
        raise FilebrowsingNotAllowed()

    full_path = Path(app.project_root) / path

    # assert that the path is inside our project root
    if not is_path_relative_to(full_path, app.project_root):
        raise InvalidPath(path)

    app.update(AppConfig(dataset=full_path))
