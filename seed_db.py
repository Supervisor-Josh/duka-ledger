from database import SessionLocal
from models import SMSTransaction, ReceiptTransaction
from datetime import datetime, timedelta

db = SessionLocal()

print("Seeding database with sample Duka data...")

# 1. Clear any old data to start fresh
db.query(SMSTransaction).delete()
db.query(ReceiptTransaction).delete()

# Current base time for sync
now = datetime.utcnow()

# 2. Add sample M-Pesa SMS Records
sms1 = SMSTransaction(
    transaction_id="RQA41MX92K",
    sender="JOHN DOE",
    amount=1500.0,
    timestamp=now,
    reconciled=False
)
sms2 = SMSTransaction(
    transaction_id="RQA52NY30L",
    sender="MARY WANJIKU",
    amount=350.0,
    timestamp=now - timedelta(minutes=30),  # Older transaction
    reconciled=False
)
db.add(sms1)
db.add(sms2)

# 3. Add sample parsed Receipt Records
# This receipt matches sms1 exactly (Same amount, only 2 minutes apart)
receipt1 = ReceiptTransaction(
    total_amount=1500.0,
    timestamp=now + timedelta(minutes=2),
    reconciled=False
)
# This receipt has no matching SMS counter-part
receipt2 = ReceiptTransaction(
    total_amount=720.0,
    timestamp=now,
    reconciled=False
)
db.add(receipt1)
db.add(receipt2)

db.commit()
db.close()
print("Database seeded successfully! Ready to test reconciliation.")
