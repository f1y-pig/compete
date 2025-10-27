import asyncio
import os

from pydantic import Field

from oxygent import MAS, Config, OxyRequest, OxyResponse, oxy
from oxygent.prompts import INTENTION_PROMPT

Config.set_agent_llm_model("default_llm")


async def workflow(oxy_request: OxyRequest):
    short_memory = oxy_request.get_short_memory()
    print("--- History record --- :", short_memory)
    master_short_memory = oxy_request.get_short_memory(master_level=True)
    print("--- History record-User layer --- :", master_short_memory)
    print("user query:", oxy_request.get_query(master_level=True))
    await oxy_request.send_message({"type": "msg_type", "content": "msg_content"})
    oxy_response = await oxy_request.call(
        callee="time_agent",
        arguments={"query": "What time is it now in Asia/Shanghai?"},
    )
    print("--- Current time --- :", oxy_response.output)
    oxy_response = await oxy_request.call(
        callee="default_llm",
        arguments={
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello!"},
            ],
            "llm_params": {"temperature": 0.6},
        },
    )
    print(oxy_response.output)
    import re

    numbers = re.findall(r"\d+", oxy_request.get_query())
    if numbers:
        n = numbers[-1]
        oxy_response = await oxy_request.call(callee="calc_pi", arguments={"prec": n})
        return f"Save {n} positions: {oxy_response.output}"
    else:
        return "Save 2 positions: 3.14, or you could ask me to save how many positions you want."


fh = oxy.FunctionHub(name="joke_tools")


@fh.tool(description="a tool for telling jokes")
async def joke_tool(joke_type: str = Field(description="The type of the jokes")):
    import random

    jokes = [
        "Teacher: Can you use the word 'because' in a sentence? \n Student: I didn't do my homework because… because I didn't do my homework.",
        "Patient: Doctor, I feel like a pair of curtains.\nDoctor: Pull yourself together!",
        "How many software engineers does it take to change a light bulb?\nNone. That's a hardware problem.",
    ]
    print("The type of the jokes", joke_type)
    return random.choice(jokes)


def update_query(oxy_request: OxyRequest) -> OxyRequest:
    print(oxy_request.shared_data)
    user_query = oxy_request.get_query(master_level=True)
    current_query = oxy_request.get_query()
    print(user_query + "\n" + current_query)
    oxy_request.arguments["who"] = oxy_request.callee
    return oxy_request


def format_output(oxy_response: OxyResponse) -> OxyResponse:
    oxy_response.output = "Answer: " + oxy_response.output
    return oxy_response


oxy_space = [
    oxy.HttpLLM(
        name="default_llm",
        api_key=os.getenv("DEFAULT_LLM_API_KEY"),
        base_url=os.getenv("DEFAULT_LLM_BASE_URL"),
        model_name=os.getenv("DEFAULT_LLM_MODEL_NAME"),
        llm_params={"temperature": 0.01},
        semaphore=4,
    ),
    oxy.ChatAgent(name="intent_agent", prompt=INTENTION_PROMPT),
    fh,
    oxy.StdioMCPClient(
        name="time_tools",
        params={
            "command": "uvx",
            "args": ["mcp-server-time", "--local-timezone=Asia/Shanghai"],
        },
    ),
    oxy.StdioMCPClient(
        name="file_tools",
        params={
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-filesystem", "./local_file"],
        },
    ),
    oxy.StdioMCPClient(
        name="math_tools",
        params={
            "command": "uv",
            "args": ["--directory", "./mcp_servers", "run", "math_tools.py"],
        },
    ),
    oxy.ReActAgent(
        name="master_agent",
        sub_agents=["time_agent", "file_agent", "math_agent"],
        additional_prompt="You may get several types of tasks, please choose correct tools to finish tasks.",
        is_master=True,
        func_format_output=format_output,
        timeout=100,
        llm_model="default_llm",
    ),
    oxy.ReActAgent(
        name="time_agent",
        desc="A tool for time query.",
        additional_prompt="Do not send other information except time.",
        tools=["time_tools"],
        func_process_input=update_query,
        trust_mode=False,
        timeout=10,
    ),
    oxy.ReActAgent(
        name="file_agent",
        desc="A tool for file operation.",
        tools=["file_tools"],
    ),
    oxy.WorkflowAgent(
        name="math_agent",
        desc="A tool for pi query",
        sub_agents=["time_agent"],
        tools=["math_tools"],
        func_workflow=workflow,
        is_retain_master_short_memory=True,
    ),
]


async def main():
    async with MAS(oxy_space=oxy_space) as mas:
        await mas.start_web_service(
            first_query="Please calculate the 20 positions of Pi",
            welcome_message="Hi, I’m OxyGent. How can I assist you?",
        )


if __name__ == "__main__":
    asyncio.run(main())
