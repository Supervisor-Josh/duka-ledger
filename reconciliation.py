from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import SMSTransaction, ReceiptTransaction  # Pulls from your actual models.py


# ==========================================
# 1. DATABASE-BOUND RECONCILIATION
# ==========================================
def reconcile_transactions(db: Session, time_window_minutes: int = 15):
    """
    Matches digital SMS transactions with cash/printed receipts directly in the database.
    Looks for matching amounts within a specific time window.
    """
    # Fetch all unmatched records
    unmatched_sms = db.query(SMSTransaction).filter(SMSTransaction.reconciled == False).all()
    unmatched_receipts = db.query(ReceiptTransaction).filter(ReceiptTransaction.reconciled == False).all()

    matches_found = 0

    for sms in unmatched_sms:
        for receipt in unmatched_receipts:
            # Check if amounts match exactly
            if sms.amount == receipt.total_amount:
                # Check if the timestamps are within the allowed time window
                time_difference = abs(sms.timestamp - receipt.timestamp)

                if time_difference <= timedelta(minutes=time_window_minutes):
                    # Link them!
                    sms.reconciled = True
                    sms.receipt_id = receipt.id

                    receipt.reconciled = True
                    receipt.sms_id = sms.id

                    db.add(sms)
                    db.add(receipt)
                    matches_found += 1
                    break  # Move to the next SMS once a match is found

    db.commit()
    return {"status": "success", "matches_created": matches_found}


# ==========================================
# 2. IN-MEMORY RECONCILIATION ENGINE
# ==========================================
class SMSTransactionPayload(BaseModel):
    transaction_id: str
    amount: float
    timestamp: datetime
    sender: str
    reconciled: bool = False


class ReceiptExpensePayload(BaseModel):
    receipt_id: str
    total_amount: float
    timestamp: datetime
    vendor: str
    reconciled: bool = False


class ReconciliationSummary(BaseModel):
    reconciled_matches: List[dict]
    unmatched_sms_outflows: List[SMSTransactionPayload]
    unmatched_ocr_expenses: List[ReceiptExpensePayload]
    total_variance: float


class DukaReconciler:
    def __init__(self, time_window_minutes: int = 60, fee_allowance: float = 0.0):
        self.time_window = timedelta(minutes=time_window_minutes)
        self.fee_allowance = fee_allowance

    def reconcile_inventory_purchases(
        self,
        sms_logs: List[SMSTransactionPayload],
        ocr_receipts: List[ReceiptExpensePayload]
    ) -> ReconciliationSummary:
        reconciled_matches = []
        unmatched_sms = list(sms_logs)
        unmatched_receipts = list(ocr_receipts)

        for sms in list(unmatched_sms):
            for receipt in list(unmatched_receipts):
                time_diff = abs(sms.timestamp - receipt.timestamp)
                amount_diff = abs(sms.amount - receipt.total_amount)

                # Match condition: within time window and amount variance tolerance
                if time_diff <= self.time_window and amount_diff <= self.fee_allowance:
                    reconciled_matches.append({
                        "sms_id": sms.transaction_id,
                        "receipt_id": receipt.receipt_id,
                        "sms_amount": sms.amount,
                        "receipt_amount": receipt.total_amount,
                        "variance": amount_diff,
                        "timestamp_matched": datetime.now()
                    })
                    
                    unmatched_sms.remove(sms)
                    unmatched_receipts.remove(receipt)
                    break

        total_sms_unmatched = sum(s.amount for s in unmatched_sms)
        total_receipts_unmatched = sum(r.total_amount for r in unmatched_receipts)
        total_variance = abs(total_sms_unmatched - total_receipts_unmatched)

        return ReconciliationSummary(
            reconciled_matches=reconciled_matches,
            unmatched_sms_outflows=unmatched_sms,
            unmatched_ocr_expenses=unmatched_receipts,
            total_variance=total_variance
        )