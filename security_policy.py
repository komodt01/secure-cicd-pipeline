def evaluate_severity(severity):
    if severity == "Critical":
        return "BLOCK"
    elif severity == "High":
        return "BLOCK"
    elif severity == "Medium":
        return "REVIEW"
    else:
        return "ALLOW"

if __name__ == "__main__":
    severity = "High"
    decision = evaluate_severity(severity)
    print(severity, decision)


