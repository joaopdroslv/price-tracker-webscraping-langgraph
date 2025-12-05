import base64
import logging

from app.config.env_variables import PLAYWRIGHT_MCP_URL
from fastmcp.client import Client
from fastmcp.client.transports import StreamableHttpTransport

logger = logging.getLogger(name=__name__)


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

    async def query_into_search_input(
        self, page_url: str, input_element_ref: str, query_text: str
    ) -> str:
        """
        Navigate to a page, type a query into a referenced search input, submit it,
        wait for results, and return a snapshot of the updated page.

        Args:
            page_url: URL where the search input exists.
            input_element_ref: The MCP element reference for the target input.
            query_text: The text to type into the search field.

        Returns:
            The snapshot text after the search action completes.
        """

        async with await self._client() as client:
            await self._open_page(client, page_url)

            await client.call_tool(
                "browser_click",
                {
                    "ref": input_element_ref,
                    "element": "search input",
                },
            )
            await client.call_tool(
                "browser_type",
                {
                    "ref": input_element_ref,
                    "element": "search input",
                    "text": query_text,
                },
            )
            await client.call_tool("browser_press_key", {"key": "Enter"})
            await client.call_tool("browser_wait_for", {"time": 5})

            result = await client.call_tool("browser_snapshot", {})
            return self._extract_text(result)
