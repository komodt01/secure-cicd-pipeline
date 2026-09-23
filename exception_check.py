import json
import sys
from datetime import date

from security_policy import evaluate_severity


with open("security-exceptions.json", "r") as file:
    exception_data = json.load(file)

with open("scout-results.sarif", "r") as file:
    scout_data = json.load(file)


exceptions = exception_data["exceptions"]
scout_findings = scout_data["runs"][0]["results"]

exception_lookup = {
    item["vulnerability_id"]: item
    for item in exceptions
}

print("Scout findings:", len(scout_findings))

overall_decision = "ALLOW"
today = date.today()


# Evaluate each Docker Scout vulnerability against the exception registry.
for finding in scout_findings:
    vulnerability_id = finding["ruleId"]

    if vulnerability_id not in exception_lookup:
        print(vulnerability_id, "NO EXCEPTION")
        overall_decision = "BLOCK"
        continue

    matched_exception = exception_lookup[vulnerability_id]

    status = matched_exception["status"]
    expiration = date.fromisoformat(
        matched_exception["expiration_date"]
    )

    if status == "APPROVED" and today <= expiration:
        print(vulnerability_id, "VALID EXCEPTION")
    else:
        print(vulnerability_id, "INVALID OR EXPIRED EXCEPTION")
        overall_decision = "BLOCK"


# Report the policy state of every registered exception.
print("\nRegistered security exceptions:")

for exception in exceptions:
    vulnerability_id = exception["vulnerability_id"]
    severity = exception["severity"]
    status = exception["status"]
    expiration_date = exception["expiration_date"]

    expiration = date.fromisoformat(expiration_date)
    decision = evaluate_severity(severity)

    if (
        decision == "BLOCK"
        and status == "APPROVED"
        and today <= expiration
    ):
        decision = "EXCEPTION"

    print(
        vulnerability_id,
        severity,
        decision,
        status,
        expiration_date,
        today,
    )


print("\nOverall container security decision:", overall_decision)

if overall_decision == "BLOCK":
    sys.exit(1)

sys.exit(0)
