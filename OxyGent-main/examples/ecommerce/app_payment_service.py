# examples/ecommerce/app_payment_service.py

import os

from oxygent import MAS, Config, oxy

Config.set_app_name("payment-service")
Config.set_server_port(8082)

oxy_space = [
    oxy.HttpLLM(
        name="default_name",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.01},
        semaphore=4,
    ),
    # Paying tool
    oxy.StdioMCPClient(
        name="payment_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "payment_tools.py"],
        },
    ),
    # Paying agent
    oxy.ReActAgent(
        name="payment_service",
        is_master=True,
        tools=["payment_tools"],
        llm_model="default_name",
    ),
]


async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
