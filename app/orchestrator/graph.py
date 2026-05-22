import logging

from app.schemas.pipeline import PipelineState
from app.orchestrator.nodes import (
    parse_document_node,
    normalize_resume_node,
    analyze_jd_node,
    score_ats_node,
    generate_resume_node,
)
from app.orchestrator.edges import route_after_normalize, route_after_jd

logger = logging.getLogger(__name__)


def build_pipeline_graph():
    """Build the LangGraph pipeline graph for the resume AI system."""
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(PipelineState)

        # Add nodes
        graph.add_node("parse_document", parse_document_node)
        graph.add_node("normalize_resume", normalize_resume_node)
        graph.add_node("analyze_jd", analyze_jd_node)
        graph.add_node("score_ats", score_ats_node)
        graph.add_node("generate_resume", generate_resume_node)

        # Entry point
        graph.set_entry_point("parse_document")

        # Sequential flow
        graph.add_edge("parse_document", "normalize_resume")

        # Conditional: after normalize, go to score if JD exists, else wait
        graph.add_conditional_edges(
            "normalize_resume",
            route_after_normalize,
            {"score": "score_ats", "wait": END},
        )

        # Conditional: after JD analysis, go to score if resume exists, else wait
        graph.add_conditional_edges(
            "analyze_jd",
            route_after_jd,
            {"score": "score_ats", "wait": END},
        )

        # Score → Generate
        graph.add_edge("score_ats", "generate_resume")
        graph.add_edge("generate_resume", END)

        return graph.compile()

    except ImportError:
        logger.warning("LangGraph not available, pipeline will use direct calls")
        return None
