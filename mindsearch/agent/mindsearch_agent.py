import json
import logging
import re
from copy import deepcopy
from typing import Dict, Tuple, Optional

from lagent.schema import AgentMessage, AgentStatusCode, ModelStatusCode
from lagent.utils import GeneratorWithReturn

from .graph import ExecutionAction, WebSearchGraph
from .streaming import AsyncStreamingAgentForInternLM, StreamingAgentForInternLM

# Configure logging
logger = logging.getLogger(__name__)


def _update_ref(ref: str, ref2url: Dict[str, str], ptr: int) -> Tuple[str, Dict[int, str], int]:
    """Update reference indices and URLs with proper error handling."""
    try:
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
                if ref2url:
                    updated_ref2url = {
                        numbers[idx] + ptr: ref2url[idx] for idx in numbers if idx in ref2url
                    }
            except (AssertionError, KeyError) as exc:
                logger.warning(f"Reference mapping issue: {str(exc)}")
                # Continue with partial mapping
                if ref2url:
                    updated_ref2url = {
                        numbers[idx] + ptr: ref2url.get(idx, f"missing_ref_{idx}") 
                        for idx in numbers if idx in ref2url
                    }
        return updated_ref, updated_ref2url, len(numbers)
    except Exception as e:
        logger.error(f"Error updating references: {e}")
        return ref, {}, 0


def _validate_memory_structure(memory: Dict) -> bool:
    """Validate that memory has the expected structure for processing."""
    try:
        if "agent.memory" not in memory:
            logger.debug("Missing 'agent.memory' in memory structure")
            return False
        
        agent_memory = memory["agent.memory"]
        if not isinstance(agent_memory, list):
            logger.debug("'agent.memory' is not a list")
            return False
        
        if len(agent_memory) < 3:
            logger.debug(f"'agent.memory' has insufficient length: {len(agent_memory)}")
            return False
        
        # Check if the third element (index 2) has the expected structure
        if not isinstance(agent_memory[2], dict):
            logger.debug("Memory element at index 2 is not a dict")
            return False
        
        if "sender" not in agent_memory[2]:
            logger.debug("Missing 'sender' in memory element at index 2")
            return False
        
        if "content" not in agent_memory[2]:
            logger.debug("Missing 'content' in memory element at index 2")
            return False
        
        return True
    except Exception as e:
        logger.error(f"Error validating memory structure: {e}")
        return False


def _extract_references_from_content(content: str) -> Optional[Dict[int, str]]:
    """Extract reference URLs from memory content with error handling."""
    try:
        if isinstance(content, str):
            parsed_content = json.loads(content)
        elif isinstance(content, dict):
            parsed_content = content
        else:
            logger.warning(f"Unexpected content type: {type(content)}")
            return None
        
        if isinstance(parsed_content, dict):
            # Convert string keys to integers
            ref2url = {
                int(k): v for k, v in parsed_content.items() 
                if str(k).isdigit() and isinstance(v, str)
            }
            return ref2url
        else:
            logger.warning(f"Parsed content is not a dict: {type(parsed_content)}")
            return None
            
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON content: {e}")
        return None
    except (ValueError, TypeError) as e:
        logger.warning(f"Error processing content: {e}")
        return None


def _generate_references_from_graph(graph: Dict[str, dict]) -> Tuple[str, Dict[int, str]]:
    """Generate references from graph with improved error handling and validation."""
    ptr, references, references_url = 0, [], {}
    
    for name, data_item in graph.items():
        if name in ["root", "response"]:
            continue
        
        logger.debug(f"Processing node: {name}")
        
        # Validate memory structure
        if "memory" not in data_item:
            logger.debug(f"Node {name}: missing 'memory' field")
            continue
        
        if not _validate_memory_structure(data_item["memory"]):
            logger.debug(f"Node {name}: invalid memory structure")
            continue
        
        agent_memory = data_item["memory"]["agent.memory"]
        
        # Check if sender is ActionExecutor
        if not agent_memory[2]["sender"].endswith("ActionExecutor"):
            logger.debug(f"Node {name}: sender is not ActionExecutor - {agent_memory[2]['sender']}")
            continue
        
        # Extract references from content
        ref2url = _extract_references_from_content(agent_memory[2]["content"])
        if ref2url is None:
            logger.debug(f"Node {name}: failed to extract references")
            continue
        
        # Get response content
        response_content = ""
        if "response" in data_item and isinstance(data_item["response"], dict):
            response_content = data_item["response"].get("content", "")
        
        if not response_content:
            logger.debug(f"Node {name}: no response content available")
            continue
        
        # Update references
        try:
            updated_ref, ref2url_updated, added_ptr = _update_ref(response_content, ref2url, ptr)
            ptr += added_ptr
            
            # Add to references
            node_content = data_item.get("content", f"Node {name}")
            references.append(f'## {node_content}\n\n{updated_ref}')
            references_url.update(ref2url_updated)
            
            logger.debug(f"Node {name}: successfully processed {len(ref2url_updated)} references")
            
        except Exception as e:
            logger.warning(f"Node {name}: error updating references - {e}")
            continue
    
    result_text = "\n\n".join(references) if references else ""
    logger.info(f"Generated references from {len(references)} nodes with {len(references_url)} URLs")
    
    return result_text, references_url


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
