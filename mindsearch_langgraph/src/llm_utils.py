"""LLM utilities for MindSearch LangGraph implementation."""

from typing import List, Dict, Tuple, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
import json
import os


class SearchPlan(BaseModel):
    """Structured output for search planning."""
    sub_queries: List[str] = Field(description="List of sub-queries to search for")
    reasoning: str = Field(description="Explanation of why these sub-queries were chosen")


class SynthesizedAnswer(BaseModel):
    """Structured output for synthesized answers."""
    answer: str = Field(description="The comprehensive answer to the user's query")
    confidence: float = Field(description="Confidence score between 0 and 1")
    references: Dict[int, str] = Field(description="Numbered references to sources")


class LLMManager:
    """Manages LLM interactions for MindSearch."""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", temperature: float = 0.1):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("OPENAI_API_KEY", "mock-key-for-testing")
        )
        
        # Initialize prompts
        self.decompose_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a search query decomposer. Your task is to break down complex queries into simpler sub-queries that can be searched independently.
            
Rules:
1. Each sub-query should be self-contained and searchable
2. Avoid redundancy between sub-queries
3. Focus on different aspects of the main query
4. Limit to 3-5 sub-queries maximum

{format_instructions}"""),
            ("human", "Decompose this query into sub-queries: {query}")
        ])
        
        self.synthesize_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a research assistant that synthesizes information from multiple search results to provide comprehensive answers.

Rules:
1. Provide a clear, well-structured answer
2. Cite sources using [1], [2], etc.
3. Be objective and factual
4. Acknowledge any limitations or conflicting information
5. Assign confidence based on source quality and consistency

{format_instructions}"""),
            ("human", """Query: {query}

Search Results:
{search_results}

Synthesize a comprehensive answer with references.""")
        ])
        
        # Initialize output parsers
        self.plan_parser = PydanticOutputParser(pydantic_object=SearchPlan)
        self.answer_parser = PydanticOutputParser(pydantic_object=SynthesizedAnswer)
    
    async def decompose_query(self, query: str) -> List[str]:
        """Decompose a complex query into sub-queries."""
        try:
            # For testing without OpenAI API
            if os.getenv("OPENAI_API_KEY", "").startswith("mock"):
                return self._mock_decompose(query)
            
            prompt = self.decompose_prompt.format_messages(
                query=query,
                format_instructions=self.plan_parser.get_format_instructions()
            )
            
            response = await self.llm.ainvoke(prompt)
            plan = self.plan_parser.parse(response.content)
            return plan.sub_queries
            
        except Exception as e:
            print(f"Error decomposing query: {e}")
            # Fallback to simple decomposition
            return [query]
    
    async def synthesize_answer(self, query: str, search_results: Dict[str, List[Dict]]) -> Tuple[str, Dict[int, str], float]:
        """Synthesize an answer from search results."""
        try:
            # For testing without OpenAI API
            if os.getenv("OPENAI_API_KEY", "").startswith("mock"):
                return self._mock_synthesize(query, search_results)
            
            # Format search results for the prompt
            formatted_results = self._format_search_results(search_results)
            
            prompt = self.synthesize_prompt.format_messages(
                query=query,
                search_results=formatted_results,
                format_instructions=self.answer_parser.get_format_instructions()
            )
            
            response = await self.llm.ainvoke(prompt)
            synthesis = self.answer_parser.parse(response.content)
            
            return synthesis.answer, synthesis.references, synthesis.confidence
            
        except Exception as e:
            print(f"Error synthesizing answer: {e}")
            # Fallback response
            return f"I found information about '{query}' but encountered an error synthesizing the results.", {}, 0.3
    
    def _format_search_results(self, search_results: Dict[str, List[Dict]]) -> str:
        """Format search results for LLM consumption."""
        formatted = []
        ref_num = 1
        
        for sub_query, results in search_results.items():
            formatted.append(f"\n### Results for: {sub_query}\n")
            for result in results:
                formatted.append(f"[{ref_num}] {result.get('title', 'No title')}")
                formatted.append(f"URL: {result.get('url', 'No URL')}")
                formatted.append(f"Snippet: {result.get('snippet', 'No snippet')}\n")
                ref_num += 1
        
        return "\n".join(formatted)
    
    def _mock_decompose(self, query: str) -> List[str]:
        """Mock decomposition for testing."""
        # Simple heuristic decomposition
        if "and" in query.lower():
            parts = query.split(" and ")
            return [part.strip() for part in parts]
        elif "vs" in query.lower() or "versus" in query.lower():
            parts = query.replace(" vs ", " versus ").split(" versus ")
            return [f"What is {part.strip()}?" for part in parts] + [query]
        elif len(query.split()) > 5:
            words = query.split()
            mid = len(words) // 2
            return [
                " ".join(words[:mid]),
                " ".join(words[mid:]),
                query
            ]
        else:
            return [query]
    
    def _mock_synthesize(self, query: str, search_results: Dict[str, List[Dict]]) -> Tuple[str, Dict[int, str], float]:
        """Mock synthesis for testing."""
        total_results = sum(len(results) for results in search_results.values())
        
        answer = f"Based on {total_results} search results for '{query}':\n\n"
        references = {}
        ref_num = 1
        
        for sub_query, results in search_results.items():
            answer += f"Regarding '{sub_query}':\n"
            for result in results[:2]:  # Use first 2 results per sub-query
                answer += f"- {result.get('snippet', 'No information')} [{ref_num}]\n"
                references[ref_num] = result.get('url', 'No URL')
                ref_num += 1
            answer += "\n"
        
        confidence = min(0.9, 0.3 + (total_results * 0.1))
        
        return answer, references, confidence