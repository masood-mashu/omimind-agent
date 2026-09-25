"""
mock_data.py - Enterprise Voice Recordings & Meeting Transcripts for Omi Simulation
"""

DEMO_MEETINGS = {
    "q4_strategy": {
        "id": "q4_strategy",
        "title": "Executive Q4 AI Infrastructure & Budget Review",
        "category": "Executive Strategy",
        "duration": "14m 20s",
        "participants": ["Sarah (CFO)", "David (CTO)", "Elena (VP Product)", "Marcus (Lead Architect)"],
        "lines": [
            {"speaker": "David (CTO)", "timestamp_str": "00:05", "text": "Good morning team. We need to finalize our Q4 compute commitments and allocate budget for the new H100 GPU cluster lease."},
            {"speaker": "Sarah (CFO)", "timestamp_str": "01:20", "text": "Our Q4 runway allows up to $450,000 for infrastructure. I will review the ScaleCloud vendor contract by Friday to ensure payment terms are Net-45."},
            {"speaker": "Elena (VP Product)", "timestamp_str": "03:15", "text": "Product team cannot delay the enterprise release. We need to deploy the multi-agent customer copilot before end of month."},
            {"speaker": "Marcus (Lead Architect)", "timestamp_str": "05:40", "text": "The primary technical risk is database latency under multi-tenant load. I'll run the load testing benchmark in staging by Wednesday."},
            {"speaker": "David (CTO)", "timestamp_str": "07:10", "text": "Agreed. Let's make sure to enforce zero-trust token redaction before any logs leave the VPC. That is a critical P0 requirement."},
            {"speaker": "Sarah (CFO)", "timestamp_str": "09:30", "text": "Approved. We will go with the 128-node reserved cluster if Marcus confirms latency is under 50ms."},
            {"speaker": "Elena (VP Product)", "timestamp_str": "11:05", "text": "I will coordinate customer rollout communications with our design team by tomorrow afternoon."}
        ]
    },
    "sre_postmortem": {
        "id": "sre_postmortem",
        "title": "P0 Incident Postmortem: Global Payment Gateway Outage",
        "category": "SRE & Engineering",
        "duration": "18m 45s",
        "participants": ["Alex (SRE Lead)", "Vikram (VP Engineering)", "Chloe (Security)", "Ravi (Database Admin)"],
        "lines": [
            {"speaker": "Alex (SRE Lead)", "timestamp_str": "00:10", "text": "Team, at 03:14 UTC our primary payment API experienced an 18-minute outage due to an expired TLS certificate on the ingress proxy."},
            {"speaker": "Vikram (VP Engineering)", "timestamp_str": "02:00", "text": "This was completely preventable. Why did our automated cert-manager alerts fail to trigger escalation?"},
            {"speaker": "Chloe (Security)", "timestamp_str": "03:45", "text": "The alert webhook was silenced during last week's firewall upgrade. I'll audit all security webhook routes by EOD tomorrow."},
            {"speaker": "Ravi (Database Admin)", "timestamp_str": "06:10", "text": "Transaction queues buffered properly, so zero financial data was lost. We confirmed that all database balances reconciled."},
            {"speaker": "Alex (SRE Lead)", "timestamp_str": "08:30", "text": "Action item: I will migrate all ingress certificates to automated Let's Encrypt renewal with Prometheus monitoring by Friday."},
            {"speaker": "Vikram (VP Engineering)", "timestamp_str": "11:20", "text": "Decided: No manual certificate renewals will ever be permitted in production. Action item assigned to Alex."}
        ]
    },
    "cs_lecture": {
        "id": "cs_lecture",
        "title": "Stanford CS229: Transformer Scaling Laws & Flash Attention",
        "category": "Academic Lecture",
        "duration": "25m 10s",
        "participants": ["Prof. Andrew", "Student Alex", "Student Maya"],
        "lines": [
            {"speaker": "Prof. Andrew", "timestamp_str": "00:15", "text": "Welcome to lecture 14. Today we analyze why standard self-attention exhibits quadratic O(N squared) memory bottleneck with sequence length."},
            {"speaker": "Student Maya", "timestamp_str": "04:30", "text": "Professor, how does FlashAttention avoid the high-bandwidth memory read-write cycle?"},
            {"speaker": "Prof. Andrew", "timestamp_str": "05:10", "text": "Excellent question. FlashAttention leverages SRAM tiling to compute softmax incrementally without materializing the full N by N attention matrix."},
            {"speaker": "Prof. Andrew", "timestamp_str": "12:40", "text": "Important announcement: Everyone must submit Problem Set 4 on Triton kernel optimization by Tuesday midnight."},
            {"speaker": "Student Alex", "timestamp_str": "14:15", "text": "Will there be office hours covering GPU memory profiling before the deadline?"},
            {"speaker": "Prof. Andrew", "timestamp_str": "15:00", "text": "Yes, TA Priya will host an extra debugging clinic in Gates Hall on Monday at 4 PM."}
        ]
    }
}
