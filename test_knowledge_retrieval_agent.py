import uuid
from knowledge_retrieval_agent import run_knowledge_retrieval_agent

TEST_CASES = [
    {
        "category": "Access Management",
        "summary": "User is locked out of their email account due to a forgotten password.",
    },
    {
        "category": "Network",
        "summary": "Employee cannot connect to the office VPN from home.",
    },
    {
        "category": "Hardware",
        "summary": "The shared printer on the third floor is offline and not printing.",
    },
    {
        "category": "Unknown",
        "summary": "The office coffee machine is broken and needs repair.",
    },
]


def run_tests():
    for case in TEST_CASES:
        trace_id = str(uuid.uuid4())
        result = run_knowledge_retrieval_agent(
            ticket_id="test_ticket",
            category=case["category"],
            summary=case["summary"],
            trace_id=trace_id,
        )
        print(f"Summary: {case['summary']}")
        print(f"  Confidence: {result['confidence']:.3f}")
        for match in result["matched_articles"]:
            print(f"  Match: {match['article_id']} (title: {match['title']}, score: {match['similarity_score']:.3f})")
        print()


if __name__ == "__main__":
    run_tests()
