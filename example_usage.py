"""Example usage for AgenticPaymentTokenizedSentinel."""
import json
from client import AgenticPaymentTokenizedSentinel

def main():
    print("=== Agentic Payment Tokenized Authorization Demo ===")
    sentinel = AgenticPaymentTokenizedSentinel()
    
    # 1. User signs purchasing mandate
    mandate = sentinel.create_delegation_mandate(max_spend_usd=120.0, allowed_merchants=["Shopify Direct", "Instacart"], duration_hours=2.0)
    print("Delegation Mandate Created:", json.dumps(mandate, indent=2))
    
    # 2. Agent generates ephemeral token for order
    token = sentinel.generate_ephemeral_token(mandate["mandate_id"], merchant_name="Instacart", exact_amount_usd=54.20)
    print("\nEphemeral Token Generated:", json.dumps(token, indent=2))
    
    # 3. Settlement
    settle = sentinel.settle_delegated_charge(token["payment_token"])
    print("\nSettlement Receipt:", json.dumps(settle, indent=2))

if __name__ == "__main__":
    main()
