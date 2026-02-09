"""Example MCP client for FreshRSS MCP Server.

This demonstrates how to use the FreshRSS MCP server from a client application.
"""

import asyncio
import os
from mcp import ClientSession
from mcp.client.sse import sse_client


async def main():
    """Run example MCP client."""
    # Connect to the MCP server via SSE
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3004/sse")
    
    print(f"Connecting to FreshRSS MCP Server at {server_url}...")
    
    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()
            print("✓ Connected to server\n")
            
            # List available tools
            tools = await session.list_tools()
            print("Available tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            print()
            
            # Get unread articles
            print("Fetching unread articles...")
            result = await session.call_tool(
                "get_unread_articles",
                {"limit": 5}
            )
            print(f"Found {len(result.content)} unread articles\n")
            
            # Display articles
            for item in result.content:
                if item.type == "text":
                    import json
                    articles = json.loads(item.text)
                    for article in articles:
                        print(f"📰 {article['title']}")
                        print(f"   Feed: {article['feed_name']}")
                        print(f"   URL: {article['url']}")
                        print(f"   Summary: {article['summary'][:100]}...")
                        print()
            
            # List feeds
            print("\nFetching feeds...")
            result = await session.call_tool("list_feeds", {})
            for item in result.content:
                if item.type == "text":
                    import json
                    feeds = json.loads(item.text)
                    print(f"\nSubscribed to {len(feeds)} feeds:")
                    for feed in feeds:
                        print(f"  - {feed['name']} ({feed['unread_count']} unread)")


if __name__ == "__main__":
    asyncio.run(main())
