import json
import logging
import re
from copy import deepcopy
from typing import Dict, Tuple, Optional, Any

from lagent.schema import AgentMessage, AgentStatusCode, ModelStatusCode
from lagent.utils import GeneratorWithReturn

from .graph import ExecutionAction, WebSearchGraph
from .streaming import AsyncStreamingAgentForInternLM, StreamingAgentForInternLM


def _update_ref(ref: str, ref2url: Dict[str, str], ptr: int) -> Tuple[str, Dict[int, str], int]:
    """Update reference numbers in text and maintain URL mapping.
    
    Args:
        ref: Text containing references in [[n]] format
        ref2url: Mapping of reference numbers to URLs
        ptr: Starting reference number
        
    Returns:
        Updated text, updated URL mapping, and next pointer value
    """
    numbers = list({int(n) for n in re.findall(r"\[\[(\d+)\]\]", ref)})
    numbers = {n: idx + 1 for idx, n in enumerate(numbers)}
    updated_ref = re.sub(
        r"\[\[(\d+)\]\]",
        lambda match: f"[[{numbers[int(match.group(1))] + ptr}]]",
        ref,
    )
    updated_ref2url = {}
    if numbers:
        try:
            assert all(elem in ref2url for elem in numbers)
        except Exception as exc:
            logging.info(f"Illegal reference id: {str(exc)}")
        if ref2url:
            updated_ref2url = {
                numbers[idx] + ptr: ref2url[idx] for idx in numbers if idx in ref2url
            }
    return updated_ref, updated_ref2url, len(numbers) + 1


def _extract_search_result(memory_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract search result from memory item with better error handling.
    
    Args:
        memory_item: Memory item potentially containing search results
        
    Returns:
        Extracted search result or None if not found
    """
    try:
        # Try to extract from content.result first
        if isinstance(memory_item.get("content"), dict):
            result = memory_item["content"].get("result")
            if result:
                return result
        
        # Try formatted.return_ path
        if isinstance(memory_item.get("formatted"), dict):
            return_data = memory_item["formatted"].get("return_")
            if return_data:
                return return_data
                
        # Try direct content if it's a search result
        content = memory_item.get("content")
        if isinstance(content, str) and "[[" in content:
            return {"content": content}
            
    except Exception as e:
        logging.warning(f"Error extracting search result: {e}")
    
    return None


def _generate_references_from_graph(graph: Dict[str, dict]) -> Tuple[str, Dict[int, dict]]:
    """Generate references from search graph with improved error handling.
    
    Args:
        graph: Search graph containing nodes and their data
        
    Returns:
        Formatted references string and URL mapping
    """
    ptr, references, references_url = 0, [], {}
    
    for name, data_item in graph.items():
        if name in ["root", "response"]:
            continue
        
        try:
            # More flexible memory structure handling
            memory = data_item.get("memory", {})
            agent_memory = memory.get("agent.memory", [])
            
            # Find the search result in memory
            search_result = None
            for idx, mem_item in enumerate(agent_memory):
                if isinstance(mem_item, dict):
                    # Check if this is from ActionExecutor
                    sender = mem_item.get("sender", "")
                    if "ActionExecutor" in sender or "searcher" in sender.lower():
                        search_result = _extract_search_result(mem_item)
                        if search_result:
                            break
            
            if not search_result:
                logging.warning(f"Node {name}: No search results found in memory")
                continue
            
            # Extract content and references
            content = search_result.get("content", "")
            ref2url = search_result.get("ref2url", {})
            
            if not content:
                logging.warning(f"Node {name}: Empty content in search result")
                continue
            
            # Update references
            updated_ref, updated_ref2url, offset = _update_ref(content, ref2url, ptr)
            references.append(f"## {name}\n\n{updated_ref}")
            references_url.update(updated_ref2url)
            ptr += offset
            
        except Exception as e:
            logging.error(f"Error processing node {name}: {e}")
            continue
    
    return "\n\n".join(references), references_url


class MindSearchAgent(StreamingAgentForInternLM):
    def __init__(
        self,
        searcher_cfg: dict,
        summary_prompt: str,
        finish_condition=lambda m: "add_response_node" in m.content,
        max_turn: int = 10,
        **kwargs,
    ):
        WebSearchGraph.SEARCHER_CONFIG = searcher_cfg
        super().__init__(finish_condition=finish_condition, max_turn=max_turn, **kwargs)
        self.summary_prompt = summary_prompt
        self.action = ExecutionAction()

    def forward(self, message: AgentMessage, session_id=0, **kwargs):
        if isinstance(message, str):
            message = AgentMessage(sender="user", content=message)
        _graph_state = dict(node={}, adjacency_list={}, ref2url={})
        local_dict, global_dict = {}, globals()
        for _ in range(self.max_turn):
            last_agent_state = AgentStatusCode.SESSION_READY
            for message in self.agent(message, session_id=session_id, **kwargs):
                if isinstance(message.formatted, dict) and message.formatted.get("tool_type"):
                    if message.stream_state == ModelStatusCode.END:
                        message.stream_state = last_agent_state + int(
                            last_agent_state
                            in [
                                AgentStatusCode.CODING,
                                AgentStatusCode.PLUGIN_START,
                            ]
                        )
                    else:
                        message.stream_state = (
                            AgentStatusCode.PLUGIN_START
                            if message.formatted["tool_type"] == "plugin"
                            else AgentStatusCode.CODING
                        )
                else:
                    message.stream_state = AgentStatusCode.STREAM_ING
                message.formatted.update(deepcopy(_graph_state))
                yield message
                last_agent_state = message.stream_state
            if not message.formatted["tool_type"]:
                message.stream_state = AgentStatusCode.END
                yield message
                return

            gen = GeneratorWithReturn(
                self.action.run(message.content, local_dict, global_dict, True)
            )
            for graph_exec in gen:
                graph_exec.formatted["ref2url"] = deepcopy(_graph_state["ref2url"])
                yield graph_exec

            reference, references_url = _generate_references_from_graph(gen.ret[1])
            _graph_state.update(node=gen.ret[1], adjacency_list=gen.ret[2], ref2url=references_url)
            if self.finish_condition(message):
                message = AgentMessage(
                    sender="ActionExecutor",
                    content=self.summary_prompt,
                    formatted=deepcopy(_graph_state),
                    stream_state=message.stream_state + 1,  # plugin or code return
                )
                yield message
                # summarize the references to generate the final answer
                for message in self.agent(message, session_id=session_id, **kwargs):
                    message.formatted.update(deepcopy(_graph_state))
                    yield message
                return
            message = AgentMessage(
                sender="ActionExecutor",
                content=reference,
                formatted=deepcopy(_graph_state),
                stream_state=message.stream_state + 1,  # plugin or code return
            )
            yield message


class AsyncMindSearchAgent(AsyncStreamingAgentForInternLM):
    def __init__(
        self,
        searcher_cfg: dict,
        summary_prompt: str,
        finish_condition=lambda m: "add_response_node" in m.content,
        max_turn: int = 10,
        **kwargs,
    ):
        WebSearchGraph.SEARCHER_CONFIG = searcher_cfg
        WebSearchGraph.is_async = True
        WebSearchGraph.start_loop()
        super().__init__(finish_condition=finish_condition, max_turn=max_turn, **kwargs)
        self.summary_prompt = summary_prompt
        self.action = ExecutionAction()

    async def forward(self, message: AgentMessage, session_id=0, **kwargs):
        if isinstance(message, str):
            message = AgentMessage(sender="user", content=message)
        _graph_state = dict(node={}, adjacency_list={}, ref2url={})
        local_dict, global_dict = {}, globals()
        for _ in range(self.max_turn):
            last_agent_state = AgentStatusCode.SESSION_READY
            async for message in self.agent(message, session_id=session_id, **kwargs):
                if isinstance(message.formatted, dict) and message.formatted.get("tool_type"):
                    if message.stream_state == ModelStatusCode.END:
                        message.stream_state = last_agent_state + int(
                            last_agent_state
                            in [
                                AgentStatusCode.CODING,
                                AgentStatusCode.PLUGIN_START,
                            ]
                        )
                    else:
                        message.stream_state = (
                            AgentStatusCode.PLUGIN_START
                            if message.formatted["tool_type"] == "plugin"
                            else AgentStatusCode.CODING
                        )
                else:
                    message.stream_state = AgentStatusCode.STREAM_ING
                message.formatted.update(deepcopy(_graph_state))
                yield message
                last_agent_state = message.stream_state
            if not message.formatted["tool_type"]:
                message.stream_state = AgentStatusCode.END
                yield message
                return

            gen = GeneratorWithReturn(
                self.action.run(message.content, local_dict, global_dict, True)
            )
            for graph_exec in gen:
                graph_exec.formatted["ref2url"] = deepcopy(_graph_state["ref2url"])
                yield graph_exec

            reference, references_url = _generate_references_from_graph(gen.ret[1])
            _graph_state.update(node=gen.ret[1], adjacency_list=gen.ret[2], ref2url=references_url)
            if self.finish_condition(message):
                message = AgentMessage(
                    sender="ActionExecutor",
                    content=self.summary_prompt,
                    formatted=deepcopy(_graph_state),
                    stream_state=message.stream_state + 1,  # plugin or code return
                )
                yield message
                # summarize the references to generate the final answer
                async for message in self.agent(message, session_id=session_id, **kwargs):
                    message.formatted.update(deepcopy(_graph_state))
                    yield message
                return
            message = AgentMessage(
                sender="ActionExecutor",
                content=reference,
                formatted=deepcopy(_graph_state),
                stream_state=message.stream_state + 1,  # plugin or code return
            )
            yield message
