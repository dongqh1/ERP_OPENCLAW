"""汽车领域 Agent 工厂兼容层，复用已有 DeepAgents/LangGraph 流程。"""

from agent.main_agent import create_main_agent


async def create_car_agent(config=None, *, sandbox_id=None):
    return await create_main_agent(config, sandbox_id=sandbox_id)
