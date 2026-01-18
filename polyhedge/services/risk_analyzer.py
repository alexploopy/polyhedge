"""Risk analyzer service using Claude LLM."""

from datetime import datetime

import anthropic

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.risk import RiskAnalysis, RiskFactor
from polyhedge.services.web_search import WebSearch

logger = get_logger(__name__)


QUESTION_GENERATION_TOOL = {
    "name": "generate_search_questions",
    "description": "Generate 5 web search questions to gather context about a user's situation",
    "input_schema": {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "5 specific search questions to gather context about the user's risks",
                "minItems": 5,
                "maxItems": 5,
            },
        },
        "required": ["questions"],
    },
}


RISK_ANALYSIS_TOOL = {
    "name": "analyze_risks",
    "description": "Analyze a user's situation to identify hedgeable risk factors",
    "input_schema": {
        "type": "object",
        "properties": {
            "situation_summary": {
                "type": "string",
                "description": "Brief summary of the user's situation",
            },
            "risk_factors": {
                "type": "array",
                "description": "List of identified risk factors",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Short name for the risk factor",
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the risk",
                        },
                        "category": {
                            "type": "string",
                            "enum": [
                                "economic",
                                "political",
                                "health",
                                "tech",
                                "environmental",
                                "social",
                                "legal",
                                "other",
                            ],
                            "description": "Category of the risk",
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Keywords for searching prediction markets",
                        },
                        "search_queries": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific queries for finding relevant markets",
                        },
                    },
                    "required": [
                        "name",
                        "description",
                        "category",
                        "keywords",
                        "search_queries",
                    ],
                },
            },
            "overall_risk_level": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "Overall risk level assessment",
            },
        },
        "required": ["situation_summary", "risk_factors", "overall_risk_level"],
    },
}

QUESTION_SYSTEM_PROMPT = """You are a research assistant. Given a user's situation,
generate 5 specific web search questions to gather relevant context about their risks.
Focus on:
- Recent news about their industry, location, or specific concerns
- Economic factors (interest rates, inflation, market trends)
- Political or regulatory changes that may affect them
- Any specific events or companies they mention

Generate questions that will help understand the CURRENT state of affairs."""


SYSTEM_PROMPT = """You are a risk analysis expert using prediction markets for hedging.
Your job is to analyze a user's real-life situation and identify specific, hedgeable
risk factors.

You have been provided with web search results to give you current context.
Use this information to identify timely, relevant risks.

Focus on:
1. Identifying concrete, measurable risks (not vague concerns)
2. Risks that are likely to have corresponding prediction markets (Polymarket)
3. Economic, political, technological, health, and environmental factors
4. Both direct risks and correlated/upstream risks

For each risk factor, provide:
- A clear, concise name
- Detailed description of how it affects the user
- Relevant keywords for finding prediction markets
- Specific search queries that would find relevant markets

Think about what events, if they occurred, would negatively impact the user's
situation. These are the risks we want to hedge against.

IMPORTANT: Be realistic about the risk level. 
- "High" risk should be reserved for imminent, severe threats (e.g., active war zone, bankruptcy imminent).
- "Medium" and "Low" are appropriate for most general economic or professional concerns.
- Do not mark every concern as "High" risk. Use a balanced, calibrated assessment."""


class RiskAnalyzer:
    """Analyzes user situations to extract hedgeable risk factors."""

    def __init__(self, settings: Settings):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.model
        self.max_tokens = settings.max_tokens
        self.web_search = WebSearch(settings)
        logger.info(f"RiskAnalyzer initialized with model: {self.model}")

    def _generate_search_questions(self, situation: str) -> list[str]:
        """Generate 5 search questions to gather context about the situation."""
        logger.info("Generating search questions for situation")
        logger.debug(f"Situation: {situation[:200]}...")

        current_date = datetime.now().strftime("%B %d, %Y")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=QUESTION_SYSTEM_PROMPT,
            tools=[QUESTION_GENERATION_TOOL],
            tool_choice={"type": "tool", "name": "generate_search_questions"},
            messages=[
                {
                    "role": "user",
                    "content": f"**Current Date:** {current_date}\n\nGenerate 5 web search questions for this situation:\n\n{situation}",
                }
            ],
        )

        for block in response.content:
            if block.type == "tool_use" and block.name == "generate_search_questions":
                questions = block.input.get("questions", [])
                logger.info(f"Generated {len(questions)} search questions")
                for i, q in enumerate(questions):
                    logger.debug(f"  Q{i+1}: {q}")
                return questions
        
        logger.warning("No questions generated")
        return []

    def _format_search_results(self, results: dict[str, list[dict]]) -> str:
        """Format search results into a readable summary for the LLM."""
        logger.debug("Formatting search results")
        lines = ["## Web Search Results\n"]
        
        for query, items in results.items():
            lines.append(f"### Query: {query}")
            if not items:
                lines.append("No results found.\n")
                continue
            for item in items[:3]:  # Top 3 results per query
                lines.append(f"- **{item['title']}**")
                lines.append(f"  {item['description']}\n")
        
        formatted = "\n".join(lines)
        logger.debug(f"Formatted search results: {len(formatted)} chars")
        return formatted

    def analyze(self, situation: str) -> RiskAnalysis:
        """Analyze a user's situation and extract risk factors."""
        logger.info("=== Starting Risk Analysis ===")
        logger.info(f"Situation length: {len(situation)} chars")
        logger.debug(f"Full situation: {situation}")
        
        # Step 1: Generate search questions
        logger.info("Step 1: Generating search questions")
        questions = self._generate_search_questions(situation)
        
        # Step 2: Perform web searches (1 per second, limited to past year)
        logger.info("Step 2: Performing web searches (past year)")
        search_results = self.web_search.search_multiple(questions, delay=1.0, freshness="py")
        
        # Step 3: Format results for the LLM
        logger.info("Step 3: Formatting search results")
        context = self._format_search_results(search_results)
        logger.debug(f"Context for LLM:\n{context}")

        # Step 4: Analyze with full context
        logger.info("Step 4: Analyzing with Claude")
        current_date = datetime.now().strftime("%B %d, %Y")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            tools=[RISK_ANALYSIS_TOOL],
            tool_choice={"type": "tool", "name": "analyze_risks"},
            messages=[
                {
                    "role": "user",
                    "content": f"**Current Date:** {current_date}\n\n{context}\n\n---\n\n**User's Situation:**\n{situation}\n\nAnalyze this situation and identify hedgeable risks. Emphasize the MAIN risks that are most likely to impact the user based on the current context above.",
                }
            ],
        )
        logger.debug(f"Claude response received, usage: {response.usage}")

        # Extract tool use from response
        for block in response.content:
            if block.type == "tool_use" and block.name == "analyze_risks":
                data = block.input
                logger.info(f"Risk analysis complete: {data.get('overall_risk_level')} risk level")
                logger.debug(f"Situation summary: {data.get('situation_summary')}")
                
                risk_factors = [
                    RiskFactor(**rf) for rf in data.get("risk_factors", [])
                ]
                logger.info(f"Identified {len(risk_factors)} risk factors")
                for rf in risk_factors:
                    logger.debug(f"  - {rf.name} ({rf.category}): {rf.description[:100]}...")
                
                return RiskAnalysis(
                    situation_summary=data.get("situation_summary", ""),
                    risk_factors=risk_factors,
                    overall_risk_level=data.get("overall_risk_level", "medium"),
                )

        logger.error("No risk analysis tool use found in response")
        raise ValueError("No risk analysis tool use found in response")
