#!/usr/bin/env python
from functools import partial

import uvicorn as uvicorn
from fastapi import FastAPI
from graphene import Context
from starlette_graphene3 import GraphQLApp, make_graphiql_handler

import models
from database import db_session, init_db
from graphene_sqlalchemy.loaders_middleware import LoaderMiddleware
from schema import schema

app = FastAPI()

example_query = """
{
  allEmployees(sort: [NAME_ASC, ID_ASC]) {
    edges {
      node {
        id
        name
        department {
          id
          name
        }
        role {
          id
          name
        }
      }
    }
  }
}
"""


class GContext(Context):
    def __init__(self, request, **kwargs):
        super().__init__(request=request, **kwargs)

    def get(self, name, default=None):
        return getattr(self, name, default)


app.add_route(
    "/graphql",
    GraphQLApp(
        schema=schema,
        on_get=make_graphiql_handler(),
        middleware=[
            LoaderMiddleware(
                [
                    models.Department,
                    models.Role,
                    models.Employee,
                ]
            )
        ],
        context_value=partial(GContext, session=db_session),
    ),
)


@app.on_event("shutdown")
async def shutdown_session():
    db_session.remove()


if __name__ == "__main__":
    init_db()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=5000,
        log_level="info",
        reload=False,
        log_config=None,
    )
