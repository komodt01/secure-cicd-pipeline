import json
import sys
from security_policy import evaluate_severity
from datetime import date

with open("security-exceptions.json", "r") as file:
    exception_data =json.load(file)

with open("scout-results.sarif", "r") as file:
   scout_data = json.load(file)

exceptions = exception_data["exceptions"]
scout_findings = scout_data["runs"][0]["results"]

exception_ids = [item["vulnerability_id"] for item in exceptions]

exception_lookup = {
    item["vulnerability_id"]: item
    for item in exceptions
}

print("Exception IDs:", exception_ids)

print("Scout findings:", len(scout_findings))
overall_decision = "ALLOW"

for finding in scout_findings:
    vulnerability_id = finding["ruleId"]

    if vulnerability_id in exception_ids:
       matched_exception = exception_lookup[vulnerability_id]
       expiration = date.fromisoformat(matched_exception["expiration_date"])
       today = date.today()

       
       if matched_exception["status"] == "APPROVED" and today <= expiration:
           print(vulnerability_id, "VALID EXCEPTION")
       else:
           print(vulnerability_id, "INVALID OR EXPIRED EXCEPTION")
           overall_decision = "BLOCK"

    else:
        print(vulnerability_id, "NO EXCEPTION")
        overall_decision = "BLOCK"

print("Overall container security decision:", overall_decision)

for exception in exceptions:
    vulnerability_id = exception["vulnerability_id"]
    status    = exception["status"]
    severity  = exception["severity"]
    decision  = evaluate_severity (severity)
    expiration_date = exception["expiration_date"]
    expiration = date.fromisoformat(expiration_date)
    today = date.today()

if decision == "BLOCK" and status == "APPROVED" and today <= expiration:
    decision = "EXCEPTION"

print(vulnerability_id, severity, decision, status, expiration_date, today)

if overall_decision == "BLOCK":
   sys.exit(1)
else :
   sys.exit(0)
