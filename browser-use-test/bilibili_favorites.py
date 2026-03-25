"""Open Bilibili with Chrome profile and check login status"""
import asyncio
import subprocess
import sys
import os

# Set UTF-8 encoding
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8')

from browser_use import Agent, Browser, ChatAnthropic

async def main():
    print("Opening Bilibili with Chrome profile...")
    browser = Browser(
        headless=False,
        user_data_dir=r'C:\Users\Eureka\AppData\Local\Google\Chrome\User Data',
        profile_directory='Profile 3'
    )

    print("Starting AI agent to check favorites...")
    agent = Agent(
        task='''Go to bilibili.com and check the login status.
        If logged in, navigate to the favorites page (收藏).
        Find the default favorite folder and count how many videos/items it contains.
        Report the exact count number.
        If not logged in, report that login is needed.''',
        llm=ChatAnthropic(
            model='claude-sonnet-4-5',
            api_key='sk-ReitRV5u8UMhe2EXlZWFxZ0C5eY9DQY0AxsCi0ZfUz33oO8n',
            base_url='http://127.0.0.1:5000'
        ),
        browser=browser,
    )

    result = await agent.run()
    print("\n=== RESULT ===")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
