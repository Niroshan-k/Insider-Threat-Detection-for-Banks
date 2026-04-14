import pymongo

def setup_database():
    #connect offline
    client = pymongo.MongoClient("mongodb://localhost:27017")
    db = client["ndb_test"]

    #employee action collection
    actions = db["employee_actions"]
    actions.create_index([("employeeId", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])

    #employees Master data
    employees = db["employees"]
    employees.create_index("employeeId", unique = True)

    # customers [ both real and fraud ]
    customers = db["customers"]
    customers.create_index("customerID", unique = True)
    customers.create_index([("createdAt", pymongo.DESCENDING)])
    
    print("✅ Offline MongoDB initialized with updated NDB schemas.")
    return db

if __name__ == "__main__":
    setup_database()