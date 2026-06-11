"""LangGraph flow for syllabus creation and on-demand lesson generation."""

from __future__ import annotations

import re
import os
import time
from typing import Any, TypedDict

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

load_dotenv()

class ModuleOutline(BaseModel):
    sequence: int = Field(description="1-based sequence number")
    title: str = Field(description="Module title")

class Syllabus(BaseModel):
    modules: list[ModuleOutline]

class StudyGraphState(TypedDict, total=False):
    goal: str
    module_count: int
    outline: list[dict[str, Any]]

def _infer_module_count_from_goal(goal: str) -> int:
    match = re.search(r"(\d+)\s*day", goal, flags=re.IGNORECASE)
    if not match:
        return 10
    day_count = int(match.group(1))
    return max(5, min(day_count, 30))

def generate_syllabus(state: StudyGraphState) -> dict[str, Any]:
    goal = state["goal"]
    module_count = state.get("module_count") or _infer_module_count_from_goal(goal)

    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2,
        max_retries=6,
    )
    syllabus_llm = llm.with_structured_output(Syllabus)

    prompt = (
        "You are an expert instructional designer. "
        f"Create a learning syllabus of exactly {module_count} modules for this goal: {goal}. "
        "Each module must have a short, specific title and a correct sequence number starting from 1."
    )

    response: Syllabus = syllabus_llm.invoke(prompt)
    outline = [m.model_dump() for m in response.modules]

    if len(outline) != module_count:
        outline = outline[:module_count]
        while len(outline) < module_count:
            outline.append(
                {
                    "sequence": len(outline) + 1,
                    "title": f"Module {len(outline) + 1}",
                }
            )

    return {"module_count": module_count, "outline": outline}

def build_graph():
    builder = StateGraph(StudyGraphState)
    builder.add_node("generate_syllabus", generate_syllabus)
    builder.set_entry_point("generate_syllabus")
    builder.add_edge("generate_syllabus", END)
    return builder.compile()

def run_study_graph(goal: str, module_count: int | None = None) -> list[dict[str, Any]]:
    """
    Lightweight initial generation: returns only the syllabus outline.
    One API call creates the full day-by-day plan, and lesson content is generated later on demand.
    """
    graph = build_graph()
    payload: StudyGraphState = {"goal": goal}
    if module_count is not None:
        payload["module_count"] = module_count
    result = graph.invoke(payload)
    outline = result.get("outline", [])

    if not isinstance(outline, list):
        raise ValueError("Invalid graph output: outline is not a list")

    normalized = []
    for idx, module in enumerate(outline, start=1):
        normalized.append(
            {
                "sequence_no": int(module.get("sequence", idx)),
                "title": str(module.get("title", f"Module {idx}")),
                "content": "",
            }
        )
    return normalized


def generate_module_content(
    *,
    goal: str,
    sequence_no: int,
    title: str,
    progress_context: str = "",
    previous_modules: list[dict[str, Any]] | None = None,
) -> str:
    """
    On-demand content generation for a single scheduled module.
    This is called only when the learner requests the lesson for the current day.
    """
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_retries=6,
    )

    previous_modules = previous_modules or []
    completed_titles = ", ".join(item["title"] for item in previous_modules if item.get("title")) or "None yet"
    learner_context = progress_context.strip() or "No extra learner progress was provided."

    prompt = (
        "You are writing the next lesson in a personalized study plan.\n"
        f"Overall goal: {goal}\n"
        f"Current day: {sequence_no}\n"
        f"Current module title: {title}\n"
        f"Modules already covered: {completed_titles}\n"
        f"Learner progress/context: {learner_context}\n"
        "Write approximately 500 words of lesson content that adapts to the learner's current progress. "
        "Include: (1) what to focus on today, (2) explanation of concepts, (3) one practical exercise, "
        "(4) one checkpoint question, and (5) a short recap."
    )

    for attempt in range(5):
        try:
            return llm.invoke(prompt).content.strip()
        except Exception as exc:
            if "429" in str(exc):
                time.sleep(10)
                continue
            raise
    raise RuntimeError(f"Failed to generate content for Day {sequence_no} after multiple retries.")
