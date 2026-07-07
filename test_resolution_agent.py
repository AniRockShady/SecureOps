import uuid
from intake_agent import run_intake_agent
from knowledge_retrieval_agent import run_knowledge_retrieval_agent
from resolution_agent import run_resolution_agent

TEST_CASES = [
    "The shared printer on the third floor is offline and not printing.",
    "The office coffee machine is broken and needs repair.",
]


def run_tests():
    for text in TEST_CASES:
        trace_id = str(uuid.uuid4())

        intake_result = run_intake_agent(
            raw_request=text,
            user_id="test_user",
            company_id="test_company",
            trace_id=trace_id,
        )

        retrieval_result = run_knowledge_retrieval_agent(
            ticket_id=intake_result["ticket_id"],
            category=intake_result["category"],
            summary=intake_result["summary"],
            trace_id=trace_id,
        )

        resolution_result = run_resolution_agent(
            ticket_id=intake_result["ticket_id"],
            summary=intake_result["summary"],
            matched_articles=retrieval_result["matched_articles"],
            confidence=retrieval_result["confidence"],
            trace_id=trace_id,
        )

        print(f"Input: {text}")
        print(f"  Ticket ID: {intake_result['ticket_id']}")
        print(f"  Confidence: {retrieval_result['confidence']:.3f}")
        print(f"  Action: {resolution_result['action']}")
        if resolution_result["resolution_text"]:
            print(f"  Resolution: {resolution_result['resolution_text']}")
        if resolution_result["escalation_reason"]:
            print(f"  Escalation reason: {resolution_result['escalation_reason']}")
        print()


if __name__ == "__main__":
    run_tests()
