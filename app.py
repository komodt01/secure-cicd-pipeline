import sys

application_name = "Secure CI/CD Demo"

def display_application_name(name):
    print(name)

display_application_name(application_name)

scan_status = "PASS"

if scan_status == "PASS":
    print("Security check passed.")
else:
    print("Security check failed.")

findings = ["Low","High", "Critical"]
security_findings = [
{
    "name": "Debug message exposed",
    "severity": "Low",
    "tool": "SAST",
},
{   "name": "Outdated dependency",
    "severity": "High",
    "tool": "SCA",
},
{   "name": "Hard-coded password",  
    "severity": "Critical",
    "tool": "Secret Scanner",
}
]

def evaluate_finding(severity):
    if severity == "Critical":
        return "BLOCK"
    elif severity == "High":
        return "REVIEW"
    else:
        return "ALLOW"

overall_decision = "ALLOW"

for finding in security_findings:
    severity = finding["severity"]
    gate_decision = evaluate_finding(severity)
    print(finding["name"], severity, gate_decision)

    if gate_decision == "BLOCK":
        overall_decision = "BLOCK"

print("Overall decision:", overall_decision)

if overall_decision == "BLOCK":
    sys.exit(1)
else:
    sys.exit(0)