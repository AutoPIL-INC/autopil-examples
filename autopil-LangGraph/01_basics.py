"""
LangGraph basics: nodes, edges, conditional routing, and shared state.

Graph flow:
    START → chat → route → [verbose: trim response] or [concise: add note] → END

Run:
    .venv/bin/python 01_basics.py
"""

import os
from typing import Annotated, TypedDict
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage

load_dotenv()

# ---------------------------------------------------------------------------
# 1. STATE — the dict every node reads from and writes to
#    add_messages is a reducer: it appends instead of replacing
# ---------------------------------------------------------------------------
class State(TypedDict):
    messages: Annotated[list, add_messages]
    response_words: int   # populated after chat_node runs


# ---------------------------------------------------------------------------
# 2. LLM
# ---------------------------------------------------------------------------
llm = ChatAnthropic(
    model="claude-opus-4-8",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
)


# ---------------------------------------------------------------------------
# 3. NODES — plain functions: receive State, return a partial update dict
# ---------------------------------------------------------------------------
def chat_node(state: State) -> dict:
    """Call Claude and record how long the reply is."""
    response = llm.invoke(state["messages"])
    word_count = len(response.content.split())
    return {
        "messages": [response],
        "response_words": word_count,
    }


def trim_node(state: State) -> dict:
    """Long response path: append a truncation note (no extra LLM call)."""
    last = state["messages"][-1]
    trimmed = " ".join(last.content.split()[:60]) + "… [trimmed for brevity]"
    print(f"\n[route → trim]  Response was {state['response_words']} words — trimmed.")
    return {"messages": [AIMessage(content=trimmed)]}


def note_node(state: State) -> dict:
    """Short response path: append a follow-up prompt (no extra LLM call)."""
    print(f"\n[route → note]  Response was {state['response_words']} words — adding note.")
    return {"messages": [AIMessage(content="(Feel free to ask a follow-up!)")]}


# ---------------------------------------------------------------------------
# 4. CONDITIONAL EDGE — returns the name of the next node
# ---------------------------------------------------------------------------
def route_by_length(state: State) -> str:
    return "trim" if state["response_words"] > 80 else "note"


# ---------------------------------------------------------------------------
# 5. GRAPH
# ---------------------------------------------------------------------------
builder = StateGraph(State)

builder.add_node("chat", chat_node)
builder.add_node("trim", trim_node)
builder.add_node("note", note_node)

builder.add_edge(START, "chat")
builder.add_conditional_edges("chat", route_by_length, {"trim": "trim", "note": "note"})
builder.add_edge("trim", END)
builder.add_edge("note", END)

graph = builder.compile()


# ---------------------------------------------------------------------------
# 6. RUN
# ---------------------------------------------------------------------------
def run(user_input: str):
    print(f"\n{'='*60}")
    print(f"User: {user_input}")
    print(f"{'='*60}")

    for event in graph.stream(
        {"messages": [HumanMessage(content=user_input)], "response_words": 0},
        stream_mode="values",
    ):
        last = event["messages"][-1]
        if isinstance(last, AIMessage) and last.content:
            print(f"\nClaude:\n{last.content}")


if __name__ == "__main__":
    run("What is LangGraph in one sentence? Then ask me a follow-up question.")
