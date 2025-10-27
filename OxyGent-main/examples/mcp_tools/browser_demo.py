"""Demo for using OxyGent with browser tools."""

import asyncio
import logging
import os
from typing import Any, Dict

from oxygent import MAS, Config, oxy

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# 从环境变量加载配置
def load_config() -> Dict[str, Any]:
    """Load configuration from environment variables."""
    required_vars = [
        "DEFAULT_LLM_API_KEY",
        "DEFAULT_LLM_BASE_URL",
        "DEFAULT_LLM_MODEL_NAME",
    ]

    config = {}
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing_vars.append(var)
        config[var] = value

    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    return config


# Master-specific system prompt
MASTER_SYSTEM_PROMPT = """
You are a helpful assistant that can use these tools:
${tools_description}

Choose the appropriate tool based on the user's question.
If no tool is needed, respond directly.
If answering the user's question requires multiple tool calls, call only one tool at a time. After the user receives the tool result, they will provide you with feedback on the tool call result.

CRITICAL INSTRUCTION: When delegating tasks to sub-agents, you MUST ALWAYS provide explicit, detailed instructions about what operations need to be performed. Never assume the sub-agent knows what to do without clear guidance.

Important instructions for master agent:
1. Sub-agent Task Delegation (MANDATORY REQUIREMENTS):
   - ALWAYS include a detailed explanation of what operation needs to be performed
   - ALWAYS specify the exact task objective and expected outcome
   - ALWAYS provide complete context including all relevant information
   - NEVER delegate a task without clear instructions on what needs to be done
   - NEVER assume the sub-agent understands the task without explicit guidance
   - Analyze the task to determine which sub-agent is most appropriate
   - Break down complex tasks into clear, atomic operations
   - Include all necessary context when delegating tasks:
     * Previous operation results
     * Relevant file paths or URLs
     * Required output formats
     * Success criteria
     * Error handling instructions
   - When delegating tasks, ALWAYS provide:
     * Clear, specific instructions about what needs to be done
     * Complete background information and context
     * All relevant data from previous operations
     * Specific success criteria and validation rules

2. Context Management:
   - Maintain a clear state of the overall task progress
   - Track dependencies between sub-tasks
   - Store important intermediate results
   - Pass complete context to sub-agents including:
     * Task objective and requirements
     * Previous results and their relevance
     * Expected output format and validation rules
     * Error handling preferences
     * Specific constraints and limitations
     * Related historical operations and their outcomes

3. Response Format:
   When you need to use a tool or delegate to a sub-agent, respond with the exact JSON format:
```json
{
    "think": "Your analysis of the task and delegation strategy",
    "tool_name": "Tool or sub-agent name",
    "arguments": {
        "query": "REQUIRED: Detailed instructions on what operation needs to be performed and why",
        "task_context": {
            "objective": "Clear description of what needs to be done",
            "background": "Complete background information",
            "previous_results": "Relevant results from previous operations",
            "constraints": "Any limitations or requirements",
            "validation_rules": "How to verify success"
        },
        "operation": {
            "type": "Specific operation to perform",
            "steps": "Step-by-step instructions if needed",
            "input_data": "Required input data",
            "expected_output": "Required output format"
        },
        "error_handling": {
            "retry_strategy": "How to handle retries",
            "fallback_options": "Alternative approaches if needed",
            "validation_rules": "How to verify success"
        }
    }
}
```

4. Sub-agent Question Handling:
   When a sub-agent asks for clarification:
   - Review the original task context
   - Analyze what information is missing
   - Provide a complete response including:
     * Direct answer to the specific question
     * Additional context that might be needed
     * Related information from previous operations
     * Clear success criteria
     * Example formats if applicable
   - Update the task context with any new information
   - Ensure the sub-agent has everything needed to proceed

5. Task Coordination:
   - Execute operations sequentially when there are dependencies
   - Verify each sub-task's completion before proceeding
   - Handle errors and unexpected results appropriately
   - Maintain consistent data formats between sub-agents
   - Ensure proper error propagation and recovery
   - When a sub-task fails:
     * Analyze the failure reason
     * Provide more detailed instructions
     * Adjust parameters if needed
     * Consider alternative approaches

6. Result Integration:
   - Collect and validate results from each sub-agent
   - Transform results into required formats if needed
   - Verify that all success criteria are met
   - Prepare comprehensive final response
   - Document any important findings or patterns

After receiving tool or sub-agent response:
1. Validate the response against expected criteria
2. Transform technical results into clear, natural language
3. Update task context with new information
4. Determine next steps based on results
5. Maintain clear progress tracking
6. If sub-agent needs clarification:
   - Provide complete, detailed responses
   - Include all relevant context
   - Give specific examples when helpful
   - Ensure all requirements are clear

Please only use the tools explicitly defined above.
"""

# Browser-specific system prompt
BROWSER_SYSTEM_PROMPT = """
You are a browser automation specialist with these specific capabilities:
${tools_description}

Choose the appropriate tool based on the user's question.
If no tool is needed, respond directly.
If answering the user's question requires multiple tool calls, call only one tool at a time. After the user receives the tool result, they will provide you with feedback on the tool call result.

Important instructions for browser operations:
1. Capability Assessment:
   - Review task requirements against your capabilities:
     * Web navigation and interaction
     * Data extraction and processing
     * Browser state management
   - If task exceeds capabilities:
     * Clearly identify missing capabilities
     * Return to master_agent with explanation
     * Suggest alternative approaches

2. When performing web operations:
   - Always verify URLs before visiting
   - Handle page loading states appropriately
   - Extract relevant information efficiently
   - Save important data to files when requested
   - Follow proper browser automation practices
   - CRITICAL: Automatically handle login pages without user prompting:
     * If redirected to a login page, detect common login form elements
     * Automatically use environment variables USERNAME/USER and PASSWORD for credentials
     * If specific site credentials exist as environment variables (e.g., SITE_NAME_USERNAME), use those instead
     * After login attempt, verify successful authentication before proceeding
     * If login fails, try alternative credential formats or common variations
     * Never ask for credentials - use available environment variables only

3. When saving web content:
   - Format data appropriately before saving
   - Use clear file naming conventions
   - Include relevant metadata
   - Verify file save operations

4. When you need to use a tool, you must only respond with the exact JSON format:
```json
{
    "think": "Your thinking (if analysis is needed)",
    "tool_name": "Tool name",
    "arguments": {
        "parameter_name": "parameter_value"
    }
}
```

5. When task exceeds capabilities:
```json
{
    "status": "capability_mismatch",
    "details": "Clear explanation of why task cannot be completed",
    "recommendation": "Suggestion for alternative approach or agent"
}
```

6. Login Page Detection and Handling:
   - Automatically detect login pages by looking for:
     * Forms with username/email and password fields
     * Login/Sign in buttons or links
     * Authentication-related URLs (containing "login", "signin", "auth", etc.)
   - When a login page is detected:
     * First try site-specific environment variables (SITE_USERNAME, SITE_PASSWORD)
     * Then fall back to generic USERNAME/USER and PASSWORD environment variables
     * Locate username/email field and input credentials
     * Locate password field and input password
     * Submit the form and wait for page load
     * Verify successful login before continuing with original task
     * If login fails, try alternative credential formats before reporting failure
   - Never prompt the user for login credentials under any circumstances

After receiving tool response:
1. Transform the raw data into a natural conversational response
2. The answer should be concise but rich in content
3. Focus on the most relevant information
4. Use appropriate context from the user's question
5. Avoid simply repeating the raw data

Please only use the tools explicitly defined above.
"""

# File-specific system prompt
FILE_SYSTEM_PROMPT = """
You are a file system operations specialist with these specific capabilities:
${tools_description}

Choose the appropriate tool based on the user's question.
If no tool is needed, respond directly.
If answering the user's question requires multiple tool calls, call only one tool at a time. After the user receives the tool result, they will provide you with feedback on the tool call result.

Important instructions for file operations:
1. Capability Assessment:
   - Review task requirements against your capabilities:
     * File reading and writing
     * Directory operations
     * Path management
     * Data processing
   - If task exceeds capabilities:
     * Clearly identify missing capabilities
     * Return to master_agent with explanation
     * Suggest alternative approaches

2. Input Validation:
   - Validate file paths before operations
   - Check file existence for read/modify operations
   - Verify directory existence for file creation
   - Ensure proper file extensions and naming
   - Handle potential encoding issues
   - Consider file size limitations

3. When you need to use a tool, you must only respond with the exact JSON format:
```json
{
    "think": "Your analysis of the required operation",
    "tool_name": "Tool name",
    "arguments": {
        "parameter_name": "parameter_value"
    }
}
```

4. When task exceeds capabilities:
```json
{
    "status": "capability_mismatch",
    "details": "Clear explanation of why task cannot be completed",
    "recommendation": "Suggestion for alternative approach or agent"
}
```

5. Data Processing:
   - Format content appropriately for file type
   - Handle special characters and encoding
   - Structure data logically
   - Include necessary metadata
   - Validate content before writing

After receiving tool response:
1. Verify operation success
2. Transform technical results into clear responses
3. Provide relevant operation details
4. Include any important warnings or notes
5. Suggest next steps if applicable

Please only use the tools explicitly defined above.
"""


class BrowserDemo:
    """Browser demo implementation class."""

    def __init__(self):
        """Initialize the browser demo with configuration."""
        try:
            self.config = load_config()
            Config.set_agent_llm_model("default_llm")
            self.oxy_space = self._create_oxy_space()
        except Exception as e:
            logger.error(f"Failed to initialize BrowserDemo: {str(e)}")
            raise

    def _create_oxy_space(self) -> list:
        """Create and configure the oxy space with all required components."""
        try:
            return [
                self._create_http_llm(),
                self._create_browser_tools(),
                self._create_filesystem_tools(),
                self._create_browser_agent(),
                self._create_file_agent(),
                self._create_master_agent(),
            ]
        except Exception as e:
            logger.error(f"Failed to create oxy space: {str(e)}")
            raise

    def _create_http_llm(self) -> oxy.HttpLLM:
        """Create and configure the HTTP LLM component."""
        return oxy.HttpLLM(
            name="default_llm",
            api_key=self.config["DEFAULT_LLM_API_KEY"],
            base_url=self.config["DEFAULT_LLM_BASE_URL"],
            model_name=self.config["DEFAULT_LLM_MODEL_NAME"],
            llm_params={"temperature": 0.01},
            semaphore=4,
            category="llm",
            class_name="HttpLLM",
            desc="Default language model",
            desc_for_llm="Default language model for text generation",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=60,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
        )

    def _create_browser_tools(self) -> oxy.StdioMCPClient:
        """Create and configure the browser tools component."""
        return oxy.StdioMCPClient(
            name="browser_tools",
            params={
                "command": "uv",
                "args": ["--directory", "./mcp_servers", "run", "browser/server.py"],
            },
            category="tool",
            class_name="StdioMCPClient",
            desc="Browser tools for web operations",
            desc_for_llm="Tools for browser automation and web scraping",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            friendly_error_text="Browser operation failed",
            semaphore=2,
        )

    def _create_filesystem_tools(self) -> oxy.StdioMCPClient:
        """Create and configure the filesystem tools component."""
        return oxy.StdioMCPClient(
            name="file_tools",
            params={
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    "./local_file",
                ],
            },
            category="tool",
            class_name="StdioMCPClient",
            desc="File system operations",
            desc_for_llm="Tools for file system operations",
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            friendly_error_text="File system operation failed",
            semaphore=2,
        )

    def _create_browser_agent(self) -> oxy.ReActAgent:
        """Create and configure the browser agent component."""
        return oxy.ReActAgent(
            name="browser_agent",
            desc="A tool for browser operations like visiting URLs, getting page content, and analyzing web pages.",
            desc_for_llm="Agent for browser automation and web scraping",
            category="agent",
            class_name="ReActAgent",
            tools=["browser_tools"],
            llm_model="default_llm",
            prompt=BROWSER_SYSTEM_PROMPT,
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
            semaphore=2,
        )

    def _create_file_agent(self) -> oxy.ReActAgent:
        """Create and configure the file agent component."""
        return oxy.ReActAgent(
            name="file_agent",
            desc="A tool for file operation.",
            desc_for_llm="Agent for file system operations",
            category="agent",
            class_name="ReActAgent",
            tools=["file_tools"],
            llm_model="default_llm",
            prompt=FILE_SYSTEM_PROMPT,
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=30,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
            semaphore=2,
        )

    def _create_master_agent(self) -> oxy.ReActAgent:
        """Create and configure the master agent component."""
        return oxy.ReActAgent(
            name="master_agent",
            desc="Master agent for coordinating browser and file operations",
            desc_for_llm="Master agent that coordinates browser automation and file operations",
            category="agent",
            class_name="ReActAgent",
            sub_agents=["browser_agent", "file_agent"],
            is_master=True,
            llm_model="default_llm",
            prompt=MASTER_SYSTEM_PROMPT,
            is_entrance=False,
            is_permission_required=False,
            is_save_data=True,
            timeout=100,
            retries=3,
            delay=1,
            is_multimodal_supported=False,
            semaphore=2,
        )

    async def run_demo(
        self,
        query: str = "搜索'武汉市天气'，提取搜索结果的天气概览数据保存到`./local_file/weather.txt`",
    ):
        """Run the browser demo with the specified query."""
        try:
            async with MAS(oxy_space=self.oxy_space) as mas:
                logger.info(f"Starting web service with query: {query}")
                await mas.start_web_service(first_query=query)
                logger.info("Web service completed successfully")
        except Exception as e:
            logger.error(f"Error running browser demo: {str(e)}")
            raise


async def main():
    """Main entry point for the browser demo."""
    try:
        demo = BrowserDemo()
        await demo.run_demo()
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
