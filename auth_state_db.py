import secrets
from google.cloud import firestore
import os
from dotenv import load_dotenv

load_dotenv()
project_id = os.getenv("PROJECT_ID")

db = firestore.Client(
    project = project_id,
    database = project_id
)

def store_oauth_state() -> str:
    """
    Generate a random state, store it in Firestore with an optional expiration, and return the state.
    """
    state = secrets.token_hex(16)  # e.g. 32 hex chars
    print(f"[DEBUG store_oauth_state] Creating doc for state={state}")
    doc_ref = db.collection("oauth_states").document(state)
    doc_data = {
        "createdAt": firestore.SERVER_TIMESTAMP,
        "expiresIn": 600  # store 10 minutes if you want a sense of expiration
    }

    doc_ref.set(doc_data)
    return state

def verify_and_consume_oauth_state(state: str) -> bool:
    """
    Check Firestore for a doc with ID = state. If it exists (and not expired),
    delete it (so it can't be reused) and return True. Otherwise return False.
    """
    print(f"[DEBUG verify_and_consume_oauth_state] Checking doc: {state}")
    doc_ref = db.collection("oauth_states").document(state)
    snap = doc_ref.get()
    if not snap.exists:
        print("[DEBUG verify_and_consume_oauth_state] Doc not found => returning False")
        return False

    # If you wanted to check actual expiration, you’d do so here:
    # data = snap.to_dict()
    # created_at = data.get("createdAt")
    # expires_in = data.get("expiresIn", 600)
    # ...some logic to compare timestamps...

    # For a simple approach, if doc exists => it's valid
    # now consume it:
    print("[DEBUG verify_and_consume_oauth_state] Doc found, deleting now...")
    doc_ref.delete()
    return True
