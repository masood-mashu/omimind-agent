"""
test_mcp_server.py - Tests for OmiMind Model Context Protocol (MCP) Server
"""
import json
import pytest
from mcp_server import OmiMindMCPServer


class TestOmiMindMCPServer:
    @pytest.fixture
    def server(self):
        return OmiMindMCPServer()

    def test_handle_initialize(self, server):
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "clientInfo": {"name": "test-client"}}
        }
        response = server.handle_request(request)
        assert response["id"] == 1
        assert "serverInfo" in response["result"]
        assert response["result"]["serverInfo"]["name"] == "omimind-mcp-server"
        assert "tools" in response["result"]["capabilities"]

    def test_handle_tools_list(self, server):
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        response = server.handle_request(request)
        assert response["id"] == 2
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "search_ambient_memory" in tool_names
        assert "get_meeting_dossier" in tool_names
        assert "extract_action_items" in tool_names
        assert "schedule_followup_events" in tool_names

    def test_handle_tool_call_search_ambient_memory(self, server):
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "search_ambient_memory",
                "arguments": {"query": "vaccine temperature container"}
            }
        }
        response = server.handle_request(request)
        assert response["id"] == 3
        content = response["result"]["content"]
        assert len(content) >= 1
        assert content[0]["type"] == "text"
        data = json.loads(content[0]["text"])
        assert "query" in data
        assert "matches" in data

    def test_handle_tool_call_schedule_followup_events(self, server):
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "schedule_followup_events",
                "arguments": {
                    "transcript": "David: Let's schedule a follow-up review tomorrow at 2 PM to go over metrics."
                }
            }
        }
        response = server.handle_request(request)
        assert response["id"] == 4
        content = response["result"]["content"]
        events = json.loads(content[0]["text"])
        assert len(events) >= 1
        assert "google_calendar_url" in events[0]
