"""Quick test of browser-use with local proxy"""
import asyncio
from browser_use import Agent, Browser, ChatAnthropic

async def main():
    browser = Browser(headless=True)
    agent = Agent(
        task="Go to https://github.com/browser-use/browser-use and tell me how many stars it has",
        llm=ChatAnthropic(
            model="claude-sonnet-4-5",
            api_key="sk-ReitRV5u8UMhe2EXlZWFxZ0C5eY9DQY0AxsCi0ZfUz33oO8n",
            base_url="http://127.0.0.1:5000"
        ),
        browser=browser,
    )
    result = await agent.run()
    print("Result:", result)

asyncio.run(main())
