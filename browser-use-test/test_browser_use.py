"""Quick test of browser-use capabilities"""
import asyncio
from browser_use import Agent, Browser, ChatBrowserUse

async def main():
    browser = Browser(headless=True)
    agent = Agent(
        task="Go to https://github.com/browser-use/browser-use and tell me how many stars it has",
        llm=ChatBrowserUse(),
        browser=browser,
    )
    result = await agent.run()
    print("Result:", result)

asyncio.run(main())
