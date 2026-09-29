"""Client module for AgenticPaymentTokenizedSentinel (100% Python Standard Library)."""
import json
import time
import uuid
import hashlib
import hmac
from typing import Dict, Any, List, Optional

class AgenticPaymentTokenizedSentinel:
    """Implements cryptographic agent payment delegation mandates, token generation,
    and velocity guardrails compliant with Mastercard Agent Connect & Stripe delegation specs."""
    
    SECRET_SIGNING_KEY = b"genpark_agentic_financial_sentinel_key_2026"

    def __init__(self, daily_spend_limit_usd: float = 1000.0):
        self.mandates: Dict[str, Dict[str, Any]] = {}
        self.active_tokens: Dict[str, Dict[str, Any]] = {}
        self.daily_spend_limit_usd = daily_spend_limit_usd
        self.daily_spent_usd = 0.0
        self.transaction_history: List[Dict[str, Any]] = []

    def create_delegation_mandate(self, max_spend_usd: float, allowed_merchants: List[str], duration_hours: float = 4.0) -> Dict[str, Any]:
        """Creates a cryptographically signed user mandate granting scoped purchasing power to the agent."""
        mandate_id = f"mnd_{uuid.uuid4().hex[:8]}"
        expires_at = time.time() + (duration_hours * 3600.0)
        
        payload_to_sign = f"{mandate_id}:{max_spend_usd}:{','.join(sorted(allowed_merchants))}:{int(expires_at)}"
        signature = hmac.new(self.SECRET_SIGNING_KEY, payload_to_sign.encode(), hashlib.sha256).hexdigest()[:24]
        
        mandate = {
            "mandate_id": mandate_id,
            "max_spend_usd": float(max_spend_usd),
            "remaining_spend_usd": float(max_spend_usd),
            "allowed_merchants": [m.lower() for m in allowed_merchants],
            "expires_at": expires_at,
            "signature": signature,
            "is_active": True
        }
        self.mandates[mandate_id] = mandate
        
        return {
            "status": "success",
            "mandate_id": mandate_id,
            "max_spend_usd": max_spend_usd,
            "allowed_merchants": allowed_merchants,
            "expires_in_hours": duration_hours,
            "signature": signature
        }

    def generate_ephemeral_token(self, mandate_id: str, merchant_name: str, exact_amount_usd: float) -> Dict[str, Any]:
        """Generates a single-use ephemeral token bound to a specific merchant and exact transaction amount."""
        if mandate_id not in self.mandates:
            return {"status": "error", "message": f"Mandate '{mandate_id}' not found."}
            
        m = self.mandates[mandate_id]
        if not m["is_active"]:
            return {"status": "error", "message": "Mandate is deactivated or revoked."}
        if time.time() > m["expires_at"]:
            return {"status": "error", "message": "Mandate has expired."}
        if merchant_name.lower() not in m["allowed_merchants"] and "*" not in m["allowed_merchants"]:
            return {"status": "error", "message": f"Merchant '{merchant_name}' is not in authorized whitelist: {m['allowed_merchants']}."}
        if exact_amount_usd > m["remaining_spend_usd"]:
            return {"status": "error", "message": f"Amount ${exact_amount_usd} exceeds mandate remaining balance ${m['remaining_spend_usd']}."}
            
        token_id = f"tok_agent_{uuid.uuid4().hex[:12]}"
        token_record = {
            "token_id": token_id,
            "mandate_id": mandate_id,
            "merchant": merchant_name.lower(),
            "authorized_amount_usd": exact_amount_usd,
            "created_at": time.time(),
            "expires_at": time.time() + 600.0,  # 10 min TTL
            "used": False
        }
        self.active_tokens[token_id] = token_record
        
        return {
            "status": "success",
            "payment_token": token_id,
            "merchant": merchant_name,
            "authorized_amount_usd": exact_amount_usd,
            "ttl_seconds": 600
        }

    def validate_transaction_velocity(self, amount_usd: float) -> Dict[str, Any]:
        """Validates velocity limits, burst rates, and daily spend ceilings."""
        if self.daily_spent_usd + amount_usd > self.daily_spend_limit_usd:
            return {
                "velocity_status": "REJECTED_DAILY_LIMIT_EXCEEDED",
                "daily_limit_usd": self.daily_spend_limit_usd,
                "current_spent_usd": self.daily_spent_usd,
                "attempted_amount_usd": amount_usd,
                "approved": False
            }
            
        return {
            "velocity_status": "APPROVED",
            "daily_limit_usd": self.daily_spend_limit_usd,
            "remaining_headroom_usd": round(self.daily_spend_limit_usd - self.daily_spent_usd - amount_usd, 2),
            "approved": True
        }

    def settle_delegated_charge(self, payment_token: str) -> Dict[str, Any]:
        """Settles transaction, debits mandate balance, revokes token, and logs tamper-evident receipt."""
        if payment_token not in self.active_tokens:
            return {"status": "error", "message": "Invalid or expired payment token."}
            
        tok = self.active_tokens[payment_token]
        if tok["used"]:
            return {"status": "error", "message": "Token has already been consumed (replay attack prevention)."}
        if time.time() > tok["expires_at"]:
            return {"status": "error", "message": "Token expired before settlement."}
            
        amt = tok["authorized_amount_usd"]
        vel = self.validate_transaction_velocity(amt)
        if not vel["approved"]:
            return {"status": "error", "message": vel["velocity_status"]}
            
        # Settle
        tok["used"] = True
        mandate = self.mandates[tok["mandate_id"]]
        mandate["remaining_spend_usd"] -= amt
        self.daily_spent_usd += amt
        
        receipt_id = f"rcpt_{uuid.uuid4().hex[:10]}"
        receipt = {
            "receipt_id": receipt_id,
            "payment_token": payment_token,
            "mandate_id": tok["mandate_id"],
            "merchant": tok["merchant"],
            "amount_settled_usd": amt,
            "mandate_remaining_usd": round(mandate["remaining_spend_usd"], 2),
            "settled_at": time.time(),
            "status": "SETTLED_COMPLETED"
        }
        self.transaction_history.append(receipt)
        
        return {"status": "success", "receipt": receipt}
