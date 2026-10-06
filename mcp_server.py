"""
mcp_server.py - Model Context Protocol (MCP) Server for OmiMind Ambient Voice Memory
Allows external agents (Claude, ChatGPT, Cursor, Antigravity) to query ambient memory and orchestrate tasks.
Protocol Specification: JSON-RPC 2.0 (MCP 2024-11-05) over stdio.
"""
import json
import sys
from typing import Any

from agents.action_extractor import LyzrActionExtractor
from agents.calendar_scheduler import LyzrCalendarScheduler
from agents.orchestrator import OmiMindOrchestrator
from backend.mock_data import DEMO_MEETINGS


def _parse_simple_transcript(raw: str) -> list[dict[str, str]]:
    lines = []
    for line in raw.split("\n"):
        if ":" in line:
            sp, tx = line.split(":", 1)
            lines.append({"speaker": sp.strip(), "text": tx.strip()})
        elif line.strip():
            lines.append({"speaker": "Speaker", "text": line.strip()})
    return lines


class OmiMindMCPServer:
    def __init__(self, storage_path: str = "./qdrant_storage"):
        self.orchestrator = OmiMindOrchestrator(storage_path=storage_path)
        self.extractor = LyzrActionExtractor()
        self.scheduler = LyzrCalendarScheduler()

        self.tools = [
            {
                "name": "search_ambient_memory",
                "description": "Performs hybrid semantic and lexical recall over Omi ambient meeting transcripts stored in Qdrant vector memory.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language query, question, or keyword to retrieve from ambient memory."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of conversational utterances to return (default 4).",
                            "default": 4
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_meeting_dossier",
                "description": "Retrieves the executive briefing, key decisions, risks, action items, and calendar links for an Omi meeting session.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "meeting_id": {
                            "type": "string",
                            "description": "The ID of the meeting (e.g., 'q4_strategy', 'sre_postmortem', 'cs229_lecture')."
                        }
                    },
                    "required": ["meeting_id"]
                }
            },
            {
                "name": "extract_action_items",
                "description": "Extracts commitments, assignees, deadlines, and Jira/Kanban priorities from raw meeting conversation text.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "Raw dialogue or speaker segment text (e.g. 'Sarah: I will review the budget by Friday')."
                        }
                    },
                    "required": ["transcript"]
                }
            },
            {
                "name": "schedule_followup_events",
                "description": "Detects proposed syncs, reviews, and meetings in transcript text and generates Google Calendar and iCal links.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "transcript": {
                            "type": "string",
                            "description": "Transcript text containing scheduling intent (e.g. 'Let us schedule a follow-up tomorrow at 2 PM')."
                        }
                    },
                    "required": ["transcript"]
                }
            }
        ]

    def handle_request(self, req: dict[str, Any]) -> dict[str, Any]:
        """
        Processes standard JSON-RPC MCP requests.
        """
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {}
                    },
                    "serverInfo": {
                        "name": "omimind-mcp-server",
                        "version": "2.0.0"
                    }
                }
            }

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": self.tools
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})
            try:
                content = self._execute_tool(tool_name, args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(content, indent=2)
                            }
                        ]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }

        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found."
            }
        }
    def _execute_tool(self, name: str, args: dict[str, Any]) -> Any:
        if name == "search_ambient_memory":
            return self.orchestrator.query_semantic_memory(
                query=args.get("query", ""),
                limit=int(args.get("limit", 4)),
            )

        if name == "get_meeting_dossier":
            m_id = args.get("meeting_id")
            if m_id not in DEMO_MEETINGS:
                raise ValueError(f"Meeting '{m_id}' not found. Available: {list(DEMO_MEETINGS.keys())}")
            meeting = DEMO_MEETINGS[m_id]
            return self.orchestrator.process_session(
                session_id=meeting["id"],
                title=meeting["title"],
                transcript_lines=meeting["lines"],
            )

        if name == "extract_action_items":
            lines = _parse_simple_transcript(args.get("transcript", ""))
            return self.extractor.extract_from_transcript(lines)

        if name == "schedule_followup_events":
            lines = _parse_simple_transcript(args.get("transcript", ""))
            return self.scheduler.extract_calendar_events(lines)

        raise ValueError(f"Unknown tool: {name}")

    def run_stdio(self):
        """
        Runs the standard I/O loop reading JSON-RPC lines from stdin and emitting to stdout.
        """
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                res = self.handle_request(req)
                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_res = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()


if __name__ == "__main__":
    server = OmiMindMCPServer()
    server.run_stdio()
