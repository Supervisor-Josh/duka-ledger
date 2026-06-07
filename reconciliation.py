from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import SMSTransaction, ReceiptTransaction  # Pulls from your actual models.py

def reconcile_transactions(db: Session, time_window_minutes: int = 15):
    """
    Matches digital SMS transactions with cash/printed receipts.
    Looks for matching amounts within a specific time window.
    """
    # 1. Fetch all unmatched records
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
