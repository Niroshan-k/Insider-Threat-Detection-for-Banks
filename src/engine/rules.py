from datetime import datetime, timedelta
import random

# rule 1 -> weekend and after-hours monitoring gap
def check_after_hours(timestamp):
    # ensure timestamp is a datetime object
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    # flags activity occuring outside 8-5/ weekends. 
    # NDB bank faliure : monitoring was weaker during weekends
    is_weekend = timestamp.weekday() >= 5 #5 saturday, 6 sunday
    is_after_hours = timestamp.hour < 8 or timestamp.hour > 17

    flags = []
    if is_weekend:
        flags.append("WEEKEND_ACTIVITY")
    if is_after_hours:
        flags.append("AFTER_HOURS_ACTIVITY")

    return flags

#rule 2 -> credential abuse & password theft
def check_credential_abuse(employee_id, ip_address, db):
    if not ip_address: return []
    
    # detects if the same IP being used by multiple employee accounts simultaneously.
    # NDB : asst. manager used password of two other officers
    five_mins_ago = datetime.utcnow() - timedelta(minutes=5)
    concurrent_logins = db.employee_actions.count_documents({
        "location.ipAddress" : ip_address,
        "timestamp" : {"$gte" : five_mins_ago},
        "employeeId" : {"$ne" : employee_id}
    })

    if concurrent_logins > 0:
        return ["CREDENTIAL_ABUSE_SUSPECTED"]
    return []

# rule 3 -> third party crypto conversion
def check_suspicious_beneficiary(beneficiary_name, amount, db):
    if not beneficiary_name: return []
    
    # flags massive tranfers to new entities, especially crypto related
    # NDB: funds circulated through 'buy today' entity for crypto
    flags = []
    # in real system : check 'beneficiaries' collection.
    # for this simulation : flags keywords and large amounts.
    name_lower = beneficiary_name.lower() 
    # can use a NLP model for this
    is_related = "crypto" in name_lower or "coin" in name_lower or "exchange" in name_lower # need improvement
   
    # Ask MongoDB: Have we ever sent money to this exact name before?
    past_payments = db.employee_actions.count_documents({
        "actionType": "ELECTRONIC_TRANSFER",
        "relatedTransaction.beneficiary.name": beneficiary_name
    })
    
    # If this is 0 (or 1, meaning the transaction we are currently checking), it's brand new
    is_new_entity = past_payments <= 1
    if is_new_entity:
        flags.append("NEW_BENEFICIARY_DETECTED")
        if is_related and amount > 10_000_000:
            flags.append("HIGH_RISK_CRYPTO_TRANSFER")
    
    return flags

# rule 4 -> ghost accounts detection
def check_ghost_account(customer_id, db):
    if not customer_id: return []

    customer = db.customers.find_one({"customerId": customer_id})
    if not customer: return []
    flags = []
    # accounts less than 7 days old
    days_old = (datetime.utcnow() - customer.get("createdAt", datetime.utcnow())).days

    if days_old < 7 and not customer.get("kycVerification", False):
        flags.append("UNVERIFIED_GHOST_ACCOUNT_SUSPECTED")
    
    return flags

# main scoring function
def evaluate_employee_action(action, db):
    # ingests a signle employee action, run all rules, calculate risk
    anomaly_flags = []
    risk_score = random.uniform(0.05, 0.15)

    # Safely extract variables to prevent crashes
    timestamp = action.get("timestamp", datetime.utcnow())
    ip_address = action.get("location", {}).get("ipAddress", "")
    action_type = action.get("actionType", "")

    if action_type in ["ELECTRONIC_TRANSFER", "LOAN_APPROVAL"] and "relatedTransaction" in action:
        amount = action["relatedTransaction"].get("amount", 0)
        # Scales risk smoothly based on amount (Max normal amount is 500,000)
        risk_score += (amount / 500000) * 0.15

    time_flags = check_after_hours(timestamp)
    if time_flags:
        anomaly_flags.extend(time_flags)
        risk_score += 0.3 * len(time_flags)

    cred_flags = check_credential_abuse(action["employeeId"], ip_address, db)
    if cred_flags:
        anomaly_flags.extend(cred_flags)
        risk_score += 0.6 # big impact

    if action_type == "ELECTRONIC_TRANSFER" and "relatedTransaction" in action:
        txn = action["relatedTransaction"]
        bene_name = txn.get("beneficiary", {}).get("name", "")
        amount = txn.get("amount", 0)

        bene_flags = check_suspicious_beneficiary(bene_name, amount, db)
        if bene_flags:
            anomaly_flags.extend(bene_flags)
            risk_score += 0.4
    
    if action_type == "LOAN_APPROVAL" and "relatedTransaction" in action:
        customer_id = action["relatedTransaction"].get("customerId", "")
        ghost_flags = check_ghost_account(customer_id, db)
        if ghost_flags:
            anomaly_flags.extend(ghost_flags)
            risk_score += 0.5
    
    # cap score at 1.0
    risk_score = min(risk_score, 1.0)

    return { "riskScore": round(risk_score, 2), "anomalyFlags": anomaly_flags, "isAlert": risk_score >= 0.75 }