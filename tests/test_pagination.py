import asyncio
import graphene
import pytest
import sqlalchemy as sa
from graphene import Context
from unittest import mock

from .models import Editor
from alchql.consts import OP_ILIKE
from alchql.types import SQLAlchemyObjectType
from alchql.fields import FilterConnectionField
from alchql.node import AsyncNode
from alchql import fields
from alchql.middlewares import LoaderMiddleware


async def add_test_data(session):
    editors = [f"Editor#{num}" for num in range(100)]

    async def create_editor(name):
        await session.execute(
            sa.insert(Editor).values(
                {
                    Editor.name: name,
                }
            )
        )

    await asyncio.gather(*[create_editor(name) for name in editors])


async def get_query():
    class EditorType(SQLAlchemyObjectType):
        class Meta:
            model = Editor
            interfaces = (AsyncNode,)
            filter_fields = {
                Editor.name: [OP_ILIKE],
            }

    class Query(graphene.ObjectType):
        node = graphene.relay.Node.Field()
        editors = FilterConnectionField(
            EditorType, sort=EditorType.sort_argument()
        )

    return Query


async def get_start_end_cursor(first: int, session):
    query = """
            query {
              editors (first: """ + str(first) + """) {
                edges {
                  node {
                    id,
                    name
                  }
                }
                pageInfo {
                  startCursor
                  endCursor
                  hasPreviousPage
                  hasNextPage
                }
              }
            }
        """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )
    page_info = result.data["editors"]["pageInfo"]
    start_cursor = page_info["startCursor"]
    end_cursor = page_info["endCursor"]
    return start_cursor, end_cursor


@pytest.mark.asyncio
async def test_query_no_filters(session):
    await add_test_data(session)

    query = """
            query {
              editors {
                edges {
                  node {
                    id,
                    name
                  }
                }
                pageInfo {
                  startCursor
                  endCursor
                  hasPreviousPage
                  hasNextPage
                }
              }
            }
        """

    limit = 10
    schema = graphene.Schema(query=await get_query())
    with mock.patch.object(fields, "DEFAULT_LIMIT", limit):
        result = await schema.execute_async(
            query,
            context_value=Context(session=session),
            middleware=[
                LoaderMiddleware([Editor]),
            ],
        )
        assert len(result.data["editors"]["edges"]) == limit

        page_info = result.data["editors"]["pageInfo"]
        assert page_info["startCursor"]
        assert page_info["endCursor"]
        assert not page_info["hasPreviousPage"]
        assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_first_specified(session):
    await add_test_data(session)

    first = 50

    query = (
        """
            query {
              editors (first: """
        + str(first)
        + """) {
                edges {
                  node {
                    id,
                    name
                  }
                }
                pageInfo {
                  startCursor
                  endCursor
                  hasPreviousPage
                  hasNextPage
                }
              }
            }
        """
    )

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )
    assert len(result.data["editors"]["edges"]) == first

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert not page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_first_after_specified(session):
    await add_test_data(session)

    _, end_cursor = await get_start_end_cursor(10, session)

    query = """
        query {
          editors (first: 10, after: \"""" + end_cursor + """\") {
            edges {
              node {
                id,
                name
              }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
          }
        }
    """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#10"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_first_before_specified(session):
    await add_test_data(session)

    _, end_cursor = await get_start_end_cursor(20, session)

    query = """
            query {
              editors (first: 10, before: \"""" + end_cursor + """\") {
                edges {
                  node {
                    id,
                    name
                  }
                }
                pageInfo {
                  startCursor
                  endCursor
                  hasPreviousPage
                  hasNextPage
                }
              }
            }
        """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#0"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert not page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_first_after_before_specified(session):
    await add_test_data(session)

    start_cursor, end_cursor = await get_start_end_cursor(20, session)

    query = """
            query {
              editors (
                first: 10, 
                after: \"""" + start_cursor + """\"
                before: \"""" + end_cursor + """\"
              ) {
                edges {
                  node {
                    id,
                    name
                  }
                }
                pageInfo {
                  startCursor
                  endCursor
                  hasPreviousPage
                  hasNextPage
                }
              }
            }
        """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#1"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_last_specified(session):
    await add_test_data(session)

    query = """
        query {
          editors (last: 10, name_Ilike: "Editor") {
            edges {
              node {
                id,
                name,
              }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
          }
        }
    """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#90"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert not page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_last_after_specified(session):
    await add_test_data(session)

    _, end_cursor = await get_start_end_cursor(10, session)

    query = """
        query {
          editors (last: 10, name_Ilike: "Editor", after: \"""" + end_cursor + """\") {
            edges {
              node {
                id,
                name,
              }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
          }
        }
    """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#90"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert not page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_last_before_specified(session):
    await add_test_data(session)

    _, end_cursor = await get_start_end_cursor(20, session)

    query = """
        query {
          editors (last: 10, name_Ilike: "Editor", before: \"""" + end_cursor + """\") {
            edges {
              node {
                id,
                name,
              }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
          }
        }
    """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#9"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_last_after_before_specified(session):
    await add_test_data(session)

    start_cursor, end_cursor = await get_start_end_cursor(20, session)

    query = """
        query {
          editors (
            last: 10, 
            name_Ilike: "Editor",
            after: \"""" + start_cursor + """\", 
            before: \"""" + end_cursor + """\"
          ) {
            edges {
              node {
                id,
                name,
              }
            }
            pageInfo {
              startCursor
              endCursor
              hasPreviousPage
              hasNextPage
            }
          }
        }
    """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )

    editors = result.data["editors"]["edges"]
    assert len(editors) == 10
    assert editors[0]["node"]["name"] == "Editor#9"

    page_info = result.data["editors"]["pageInfo"]
    assert page_info["startCursor"]
    assert page_info["endCursor"]
    assert page_info["hasPreviousPage"]
    assert page_info["hasNextPage"]


@pytest.mark.asyncio
async def test_query_only_last_specified(session):
    await add_test_data(session)

    query = """
            query {
              editors (last: 1) {
                edges {
                  node {
                    id,
                    name
                  }
                }
              }
            }
        """

    schema = graphene.Schema(query=await get_query())
    result = await schema.execute_async(
        query,
        context_value=Context(session=session),
        middleware=[
            LoaderMiddleware([Editor]),
        ],
    )
    assert result.errors
