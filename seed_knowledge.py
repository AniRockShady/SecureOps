import chromadb
from chromadb import Documents, EmbeddingFunction, Embeddings
from datetime import datetime, timezone
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client_genai = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

class GeminiEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        pass

    def __call__(self, input: Documents) -> Embeddings:
        result = client_genai.models.embed_content(
            model="gemini-embedding-001",
            contents=input,
        )
        return [e.values for e in result.embeddings]


embedding_fn = GeminiEmbeddingFunction()
client = chromadb.PersistentClient(path="./chroma_data")
collection = client.get_or_create_collection(
    name="knowledge_articles",
    metadata={"hnsw:space": "cosine"},
    embedding_function=embedding_fn,
)
articles = [
    {
        "id": "password_reset_lockout",
        "title": "Account Lockout After Multiple Failed Login Attempts",
        "category": "Access Management",
        "content": (
            "Users may experience an account lockout after exceeding the maximum number "
            "of failed authentication attempts in Active Directory. To resolve this, "
            "navigate to the Active Directory Users and Computers (ADUC) console and "
            "locate the affected user account. Right-click the account, select Properties, "
            "navigate to the Account tab, and check the 'Unlock account' box. Advise the "
            "user to wait up to 15 minutes for domain controller replication before "
            "attempting to log in again."
        ),
    },
    {
        "id": "vpn_connectivity_failure",
        "title": "VPN Connection Failure and Certificate Errors",
        "category": "Network",
        "content": (
            "Remote users may report an inability to connect to the corporate VPN, often "
            "accompanied by a certificate validation error or protocol timeout. This issue "
            "is typically caused by an expired local machine certificate or a corrupted "
            "VPN client installation. First, force a manual group policy update using "
            "'gpupdate /force' to ensure the latest certificates are pushed to the "
            "endpoint. If the issue persists, perform a clean uninstallation of the VPN "
            "client, reboot the machine, and reinstall the latest approved client package "
            "from the software deployment center."
        ),
    },
    {
        "id": "email_delivery_delay",
        "title": "Outbound Email Delivery Delays and Mail Queue Buildup",
        "category": "Email",
        "content": (
            "Users may report significant delays when sending outbound emails to external "
            "domains, which is often caused by a backlog in the Exchange transport queue. "
            "Administrators should access the Exchange Management Shell and run "
            "'Get-Queue' to identify any blocked or suspended message queues. If a "
            "specific relay connector is throttling traffic, restart the Microsoft "
            "Exchange Transport service on the affected routing server and manually "
            "resume any suspended queues."
        ),
    },
    {
        "id": "shared_printer_unresponsive",
        "title": "Department Network Printer Showing Offline or Not Responding",
        "category": "Hardware",
        "content": (
            "A shared department printer may appear offline to users or fail to process "
            "incoming print jobs despite being powered on and connected to the network. "
            "Support staff should first attempt to restart the Print Spooler service on "
            "the local print server to clear any stuck documents in the queue. If "
            "restarting the spooler does not restore functionality, remove the existing "
            "printer object from the server, download the latest manufacturer drivers, "
            "and recreate the printer share."
        ),
    },
    {
        "id": "software_license_expired",
        "title": "Application Launch Blocked Due to Expired Subscription License",
        "category": "Software Licensing",
        "content": (
            "Users attempting to launch specific enterprise applications may receive an "
            "error indicating that their subscription license has expired. To resolve "
            "this, verify the user's entitlement status in the vendor's administrative "
            "portal or the internal software asset management tool. If the license was "
            "legitimately expired, direct the user to submit a formal software request "
            "ticket for manager approval to fund a new subscription. Once the new license "
            "is procured and assigned, instruct the user to sign out of the application "
            "and sign back in to refresh their local entitlement token."
        ),
    },
    {
        "id": "low_disk_space_alert",
        "title": "System Drive Critical Low Disk Space Alert",
        "category": "Infrastructure",
        "content": (
            "Automated monitoring systems may generate a critical alert when a server's "
            "system drive falls below 10% available capacity, potentially causing "
            "application crashes or system instability. The primary resolution involves "
            "identifying and purging overgrown log files, particularly IIS logs or "
            "temporary application cache files located in the system directories. To "
            "prevent recurrence, configure an automated log rotation policy or scheduled "
            "task to automatically archive and purge system logs older than thirty days."
        ),
    },
]

for article in articles:
    collection.add(
        ids=[article["id"]],
        documents=[article["content"]],
        metadatas=[{
            "title": article["title"],
            "category": article["category"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }],
    )

print(f"Ingested {len(articles)} knowledge articles into ChromaDB.")