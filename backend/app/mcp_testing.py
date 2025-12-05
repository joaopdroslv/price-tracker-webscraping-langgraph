import logging
from typing import List, TypedDict

import app.config.env_variables
import app.config.logging

logger = logging.getLogger()


import base64
import logging

from app.config.env_variables import PLAYWRIGHT_MCP_URL
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

logger = logging.getLogger(name=__name__)


class PageItem(TypedDict):

    name: str
    url: str


class PageItemResult(TypedDict):

    name: str
    url: str
    snapshot: str


class PlaywrightMcp:
    """
    A utility wrapper around a Playwright MCP server, providing simple methods
    for navigation, snapshots, screenshots, and user interactions like typing
    and clicking. Each method handles the client lifecycle and abstracts the
    MCP tool calls behind a clean interface.
    """

    def __init__(self, mcp_server_url: str = PLAYWRIGHT_MCP_URL):
        """
        Initialize the transport and prepare the MCP client connection.

        Args:
            mcp_server_url: URL of the Playwright MCP server.
        """

        self.transport = StreamableHttpTransport(mcp_server_url)

    async def _client(self) -> Client:
        """
        Create and return a new MCP client instance using the configured transport.

        Returns:
            A Client instance ready to send MCP tool calls.
        """

        return Client(self.transport)

    async def multi_tab(self):
        async with await self._client() as client:

            tools_list = await client.list_tools()
            for tool in tools_list:
                if tool.name != "browser_tabs":
                    continue
                print(tool.model_dump())

            await client.call_tool("browser_tabs", {"action": "new", "index": 333})
            await client.call_tool("browser_tabs", {"action": "new", "index": 666})
            await client.call_tool("browser_tabs", {"action": "new", "index": 999})

            result = await client.call_tool("browser_tabs", {"action": "list"})
            print("\n")
            print(result)
            print("\n")
            print(result.content[0].text)

            await client.call_tool("browser_tabs", {"action": "select", "index": 2})
            await self._open_page(client=client, url="https://www.amazon.com.br/")

            result = await client.call_tool("browser_tabs", {"action": "list"})
            print(result.content[0].text)

    # NOTE: SSE Transport does not support this method
    async def single_client(self, items: List[PageItem]) -> List[PageItemResult]:

        async with await self._client() as client:
            # Step 1: Create a tab for each PageItem
            for idx, item in enumerate(items):
                await client.call_tool("browser_tabs", {"action": "new", "index": idx})

            # Step 2: Creates palalel tasks, each task will use a specific tab
            async def process_page_item(tab_index: int, item: PageItem):

                await client.call_tool(
                    "browser_tabs", {"action": "select", "index": tab_index}
                )
                await self._open_page(client, item["url"])
                result = await client.call_tool("browser_snapshot", {})
                text = self._extract_text(result)

                return {
                    "name": item["name"],
                    "url": item["url"],
                    "snapshot": text,
                }

            tasks = [
                asyncio.create_task(process_page_item(idx, item))
                for idx, item in enumerate(items)
            ]

            # Step 3: Execute each task in paralel
            results = await asyncio.gather(*tasks)

            return results

    async def multiple_clients(self, items: List[PageItem]) -> List[PageItemResult]:

        async def process_page_item(item: PageItem):
            async with await self._client() as client:
                await self._open_page(client, item["url"])
                result = await client.call_tool(
                    "browser_take_screenshot", {"fullPage": True, "type": "png"}
                )
                img = self._extract_image_bytes(result)
                if img:
                    filename = item["name"] + ".png"
                    with open(filename, "wb") as f:
                        f.write(img)
                result = await client.call_tool("browser_snapshot", {})
                return {
                    "name": item["name"],
                    "url": item["url"],
                    "snapshot": self._extract_text(result),
                }

        # Execute only 10 PageItem's simultaneously
        semaphore = asyncio.Semaphore(5)

        async def worker(item):
            """Wrapper to use the asyncio.Semaphore and limit the simultaneous execution."""

            async with semaphore:
                return await process_page_item(item)

        return await asyncio.gather(*(worker(item) for item in items))

        # tasks = [asyncio.create_task(process_page_item(item)) for item in items]
        # return await asyncio.gather(*tasks)

    async def _open_page(self, client: Client, url: str) -> None:
        """
        Navigate to a page and wait briefly to allow it to load.

        Args:
            client: The active MCP client.
            url: URL to navigate to.
        """

        await client.call_tool("browser_navigate", {"url": url})
        await client.call_tool("browser_wait_for", {"time": 5})

    def _extract_text(self, result) -> str:
        """
        Extract plain text from a snapshot or tool result.

        Args:
            result: The MCP tool result.

        Returns:
            The extracted text content, or an empty string if unavailable.
        """

        return result.content[0].text if result.content else ""

    def _extract_image_bytes(self, result):
        """
        Extract raw image bytes from a tool result.

        Args:
            result: The MCP tool result.

        Returns:
            Decoded image bytes if found, otherwise None.
        """

        for item in result.content:
            if getattr(item, "type", None) == "image":
                return base64.b64decode(item.data)
        return None

    async def extract_snapshot(self, page_url: str) -> str:
        """
        Navigate to a page and return its textual snapshot representation.

        Args:
            page_url: URL of the page to capture.

        Returns:
            A string containing snapshot text of the page.
        """

        async with await self._client() as client:
            await self._open_page(client, page_url)
            result = await client.call_tool("browser_snapshot", {})
            return self._extract_text(result)

    async def take_screenshot(
        self, page_url: str, filename: str, full_page: bool = True
    ) -> None:
        """
        Navigate to a page, take a screenshot, and save it to a file.

        Args:
            page_url: URL to capture.
            filename: Path to save the screenshot.
            full_page: Whether the screenshot should capture the full page.
        """

        async with await self._client() as client:
            await self._open_page(client, page_url)
            result = await client.call_tool(
                "browser_take_screenshot", {"fullPage": full_page, "type": "png"}
            )
            img = self._extract_image_bytes(result)
            if img:
                with open(filename, "wb") as f:
                    f.write(img)


items = [
    PageItem(
        name="ASUS TUF Gaming Notebook",
        # url="https://www.amazon.com.br/ASUS-Gaming-Intel-KeepOS-Mecha/dp/B0F6GGBRYR/?_encoding=UTF8&pd_rd_w=zOgjE&content-id=amzn1.sym.8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_p=8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_r=FGHR7HA413PZ01FQ86X8&pd_rd_wg=vwG0C&pd_rd_r=b3fe69ec-8514-4c7f-81e9-575b6290635c&ref_=pd_hp_d_atf_unk",
        url="https://www.amazon.com.br/ASUS-Gaming-Intel-KeepOS-Mecha/dp/B0F6GGBRYR",
    ),
    PageItem(
        name="Notebook ASUS Vivobook",
        # url="https://www.amazon.com.br/Notebook-ASUS-Vivobook-Intel-X1504VA-NJ1745W/dp/B0F4M66XWL/?_encoding=UTF8&pd_rd_w=zOgjE&content-id=amzn1.sym.8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_p=8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_r=FGHR7HA413PZ01FQ86X8&pd_rd_wg=vwG0C&pd_rd_r=b3fe69ec-8514-4c7f-81e9-575b6290635c&ref_=pd_hp_d_atf_unk",
        url="https://www.amazon.com.br/Notebook-ASUS-Vivobook-Intel-X1504VA-NJ1745W/dp/B0F4M66XWL",
    ),
    PageItem(
        name="Bundle Nintendo Switch 2 + 2 Jogos",
        # url="https://www.amazon.com.br/Bundle-Nintendo-Switch-Digital-Mario/dp/B0F67B2D45/?_encoding=UTF8&pd_rd_w=zOgjE&content-id=amzn1.sym.8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_p=8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_r=FGHR7HA413PZ01FQ86X8&pd_rd_wg=vwG0C&pd_rd_r=b3fe69ec-8514-4c7f-81e9-575b6290635c&ref_=pd_hp_d_atf_unk&th=1",
        url="https://www.amazon.com.br/Bundle-Nintendo-Switch-Digital-Mario/dp/B0F67B2D45",
    ),
    PageItem(
        name="Celular Samsung Galaxy S25",
        # url="https://www.amazon.com.br/Celular-Samsung-Galaxy-C%C3%A2mera-Tripla/dp/B0DSXX6XB3/?_encoding=UTF8&pd_rd_w=zOgjE&content-id=amzn1.sym.8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_p=8531100d-ca88-45dd-ba21-de3dd971a698&pf_rd_r=FGHR7HA413PZ01FQ86X8&pd_rd_wg=vwG0C&pd_rd_r=b3fe69ec-8514-4c7f-81e9-575b6290635c&ref_=pd_hp_d_atf_unk&th=1",
        url="https://www.amazon.com.br/Celular-Samsung-Galaxy-C%C3%A2mera-Tripla/dp/B0DSXX6XB3",
    ),
]


async def execute():

    mcp = PlaywrightMcp()

    result: List[PageItemResult] = await mcp.multiple_clients(items=items)

    for item in result:
        print("\n")
        print(item["name"])
        print(f"\t* Success? [ {True if item['snapshot'] else False} ]")
        print(f"\t* Snapshot lenght [ {len(item['snapshot'])} ]")


async def take_screenshot():
    """Wrapper function to call the take_screenshot MCP tool."""

    mcp = PlaywrightMcp()
    filename = "output.png"

    logger.info("Taking a full page screenshot of the page.")
    await mcp.take_screenshot(
        page_url="https://www.amazon.com.br/",
        filename=filename,
    )
    logger.info(f'Full page screenshot saved into "{filename}" file.')


if __name__ == "__main__":
    import asyncio

    asyncio.run(execute())
